import os
from typing import TYPE_CHECKING, List, Optional

import huggingface_hub
import torch
from toolkit.config_modules import GenerateImageConfig, ModelConfig
from toolkit.metadata import get_meta_for_safetensors
from toolkit.models.base_model import BaseModel
from toolkit.basic import flush
from toolkit.prompt_utils import PromptEmbeds
from toolkit.samplers.custom_flowmatch_sampler import (
    CustomFlowMatchEulerDiscreteScheduler,
)
from toolkit.accelerator import unwrap_model
from optimum.quanto import QTensor

from transformers import AutoProcessor, Mistral3ForConditionalGeneration
from toolkit.models.v2.text_encoders.mistral3 import Mistral3TextEncoder
from .src.model import Flux2, Flux2Params
from .src.pipeline import Flux2Pipeline
from toolkit.models.v2.vae.flux2_kl import (
    AutoEncoder,
    AutoEncoderParams,
    AutoEncoderSmallDecoderParams,
)
from safetensors.torch import load_file, save_file
from PIL import Image

if TYPE_CHECKING:
    from toolkit.data_transfer_object.data_loader import DataLoaderBatchDTO

from .src.sampling import (
    batched_prc_img,
    batched_prc_txt,
    default_prep,
    encode_image_refs,
    pack_encoded_refs,
    scatter_ids,
)

scheduler_config = {
    "base_image_seq_len": 256,
    "base_shift": 0.5,
    "max_image_seq_len": 4096,
    "max_shift": 1.15,
    "num_train_timesteps": 1000,
    "shift": 3.0,
    "use_dynamic_shifting": True,
}

MISTRAL_PATH = "mistralai/Mistral-Small-3.1-24B-Instruct-2503"
FLUX2_VAE_FILENAME = "ae.safetensors"
FLUX2_TRANSFORMER_FILENAME = "flux2-dev.safetensors"

HF_TOKEN = os.getenv("HF_TOKEN", None)


class Flux2Model(BaseModel):
    arch = "flux2"
    flux2_te_type: str = "mistral"  # "mistral" or "qwen"
    flux2_vae_path: str = None
    flux2_te_filename: str = FLUX2_TRANSFORMER_FILENAME
    flux2_is_guidance_distilled: bool = True

    def __init__(
        self,
        device,
        model_config: ModelConfig,
        dtype="bf16",
        custom_pipeline=None,
        noise_scheduler=None,
        **kwargs,
    ):
        super().__init__(
            device, model_config, dtype, custom_pipeline, noise_scheduler, **kwargs
        )
        self.is_flow_matching = True
        self.is_transformer = True
        self.target_lora_modules = ["Flux2"]
        # control images will come in as a list for encoding some things if true
        self.has_multiple_control_images = True
        # do not resize control images
        self.use_raw_control_images = True

    # static method to get the noise scheduler
    @staticmethod
    def get_train_scheduler():
        return CustomFlowMatchEulerDiscreteScheduler(**scheduler_config)

    def get_bucket_divisibility(self):
        return 16

    def get_flux2_params(self):
        return Flux2Params()

    def load_te(self):
        dtype = self.torch_dtype
        self.print_and_status_update("Loading Mistral")

        # load + quantize + offload + placement, all driven by model_config
        # tie_word_embeddings=False: the checkpoint carries both embed_tokens
        # and lm_head with different values; the config's tie claim is wrong
        text_encoder = Mistral3TextEncoder.load(
            MISTRAL_PATH,
            subfolder="",
            tie_word_embeddings=False,
            **self.component_load_kwargs("te"),
        )
        flush()

        # fix_mistral_regex=False: keep the exact tokenization flux2 has always
        # used (True would change the pre-tokenizer and shift conditioning)
        tokenizer = AutoProcessor.from_pretrained(
            MISTRAL_PATH, fix_mistral_regex=False
        )
        return text_encoder, tokenizer

    def load_model(self):
        dtype = self.torch_dtype
        self.print_and_status_update("Loading Flux2 model")
        # will be updated if we detect a existing checkpoint in training folder
        model_path = self.model_config.name_or_path
        transformer_path = model_path

        self.print_and_status_update("Loading transformer")
        # use local path if provided
        if os.path.exists(os.path.join(transformer_path, self.flux2_te_filename)):
            transformer_path = os.path.join(transformer_path, self.flux2_te_filename)

        if not os.path.exists(transformer_path):
            # assume it is from the hub
            transformer_path = huggingface_hub.hf_hub_download(
                repo_id=model_path,
                filename=self.flux2_te_filename,
                token=HF_TOKEN,
            )

        transformer_state_dict = load_file(transformer_path, device="cpu")
        transformer = Flux2.load_from_state_dict(
            transformer_state_dict, dtype, config=self.get_flux2_params()
        )

        # quantize + offload + placement, all driven by model_config
        transformer.aitk_post_load(**self.component_load_kwargs("transformer"))
        flush()

        text_encoder, tokenizer = self.load_te()

        self.print_and_status_update("Loading VAE")
        vae_path = self.model_config.vae_path

        if os.path.exists(os.path.join(model_path, FLUX2_VAE_FILENAME)):
            vae_path = os.path.join(model_path, FLUX2_VAE_FILENAME)

        if vae_path is None:
            vae_path = self.flux2_vae_path

        if vae_path is None or not os.path.exists(vae_path):
            vae_filename = FLUX2_VAE_FILENAME
            if vae_path is not None:
                # see if it is a filename for huggingface hub
                if len(vae_path.split("/")) == 3 and vae_path.endswith(".safetensors"):
                    vae_filename = vae_path.split("/")[-1]
                    vae_path = "/".join(vae_path.split("/")[:-1])
            p = vae_path if vae_path is not None else model_path
            # assume it is from the hub
            vae_path = huggingface_hub.hf_hub_download(
                repo_id=p,
                filename=vae_filename,
                token=HF_TOKEN,
            )
        
        # config sniffed from the checkpoint (small-decoder detection)
        vae = AutoEncoder.load_model(vae_path, dtype=dtype)

        self.noise_scheduler = Flux2Model.get_train_scheduler()

        self.print_and_status_update("Making pipe")

        pipe: Flux2Pipeline = Flux2Pipeline(
            scheduler=self.noise_scheduler,
            text_encoder=text_encoder,
            tokenizer=tokenizer,
            vae=vae,
            transformer=None,
            text_encoder_type=self.flux2_te_type,
            is_guidance_distilled=self.flux2_is_guidance_distilled,
        )
        # for quantization, it works best to do these after making the pipe
        pipe.transformer = transformer

        self.print_and_status_update("Preparing Model")

        text_encoder = [pipe.text_encoder]
        tokenizer = [pipe.tokenizer]

        flush()
        # just to make sure everything is on the right device and dtype
        if self.model_config.low_vram:
            text_encoder[0].to("cpu")
        else:
            text_encoder[0].to(self.device_torch)
        text_encoder[0].requires_grad_(False)
        text_encoder[0].eval()
        if self.model_config.low_vram:
            pipe.transformer = pipe.transformer.to("cpu")
        else:
            pipe.transformer = pipe.transformer.to(self.device_torch)
        flush()

        # save it to the model class
        self.vae = vae
        self.text_encoder = text_encoder  # list of text encoders
        self.tokenizer = tokenizer  # list of tokenizers
        self.model = pipe.transformer
        self.pipeline = pipe
        self.print_and_status_update("Model Loaded")

    def get_generation_pipeline(self):
        scheduler = Flux2Model.get_train_scheduler()

        pipeline: Flux2Pipeline = Flux2Pipeline(
            scheduler=scheduler,
            text_encoder=unwrap_model(self.text_encoder[0]),
            tokenizer=self.tokenizer[0],
            vae=unwrap_model(self.vae),
            transformer=unwrap_model(self.transformer),
            text_encoder_type=self.flux2_te_type,
            is_guidance_distilled=self.flux2_is_guidance_distilled,
        )

        pipeline = pipeline.to(self.device_torch)

        return pipeline

    def generate_single_image(
        self,
        pipeline: Flux2Pipeline,
        gen_config: GenerateImageConfig,
        conditional_embeds: PromptEmbeds,
        unconditional_embeds: PromptEmbeds,
        generator: torch.Generator,
        extra: dict,
    ):
        gen_config.width = (
            gen_config.width // self.get_bucket_divisibility()
        ) * self.get_bucket_divisibility()
        gen_config.height = (
            gen_config.height // self.get_bucket_divisibility()
        ) * self.get_bucket_divisibility()

        control_img_list = []
        if gen_config.ctrl_img is not None:
            control_img = Image.open(gen_config.ctrl_img)
            control_img = control_img.convert("RGB")
            control_img_list.append(control_img)
        elif gen_config.ctrl_img_1 is not None:
            control_img = Image.open(gen_config.ctrl_img_1)
            control_img = control_img.convert("RGB")
            control_img_list.append(control_img)
        if gen_config.ctrl_img_2 is not None:
            control_img = Image.open(gen_config.ctrl_img_2)
            control_img = control_img.convert("RGB")
            control_img_list.append(control_img)
        if gen_config.ctrl_img_3 is not None:
            control_img = Image.open(gen_config.ctrl_img_3)
            control_img = control_img.convert("RGB")
            control_img_list.append(control_img)

        if not self.flux2_is_guidance_distilled:
            extra["negative_prompt_embeds"] = unconditional_embeds.text_embeds

        img = pipeline(
            prompt_embeds=conditional_embeds.text_embeds,
            height=gen_config.height,
            width=gen_config.width,
            num_inference_steps=gen_config.num_inference_steps,
            guidance_scale=gen_config.guidance_scale,
            latents=gen_config.latents,
            generator=generator,
            control_img_list=control_img_list,
            **extra,
        ).images[0]
        return img

    def get_noise_prediction(
        self,
        latent_model_input: torch.Tensor,
        timestep: torch.Tensor,  # 0 to 1000 scale
        text_embeddings: PromptEmbeds,
        guidance_embedding_scale: float,
        batch: "DataLoaderBatchDTO" = None,
        **kwargs,
    ):
        with torch.no_grad():
            txt, txt_ids = batched_prc_txt(text_embeddings.text_embeds)
            packed_latents, img_ids = batched_prc_img(latent_model_input)

            img_cond_seq: torch.Tensor | None = None
            img_cond_seq_ids: torch.Tensor | None = None

            cached_ctrl = getattr(batch, "cached_control_latents_list", None)

            if cached_ctrl is not None and len(cached_ctrl) > 0:
                for sample_latents in cached_ctrl:
                    if not sample_latents:
                        continue
                    encoded_refs = [lat.to(self.device_torch) for lat in sample_latents]
                    seq_item, ids_item = pack_encoded_refs(encoded_refs)
                    if img_cond_seq is None:
                        img_cond_seq = seq_item
                        img_cond_seq_ids = ids_item
                    else:
                        img_cond_seq = torch.cat((img_cond_seq, seq_item), dim=0)
                        img_cond_seq_ids = torch.cat((img_cond_seq_ids, ids_item), dim=0)
            else:
                batch_control_tensor_list = batch.control_tensor_list
                if batch_control_tensor_list is None and batch.control_tensor is not None:
                    batch_control_tensor_list = []
                    for b in range(latent_model_input.shape[0]):
                        batch_control_tensor_list.append(batch.control_tensor[b : b + 1])

                if batch_control_tensor_list is not None:
                    batch_size, _num_channels_latents, height, width = (
                        latent_model_input.shape
                    )
                    target_pixels = (
                        height
                        * self.pipeline.vae_scale_factor
                        * width
                        * self.pipeline.vae_scale_factor
                    )
                    match_target_res = self.model_config.model_kwargs.get(
                        "match_target_res", False
                    )

                    if len(batch_control_tensor_list) != batch_size:
                        raise ValueError(
                            "Control tensor list length does not match batch size"
                        )
                    for control_tensor_list in batch_control_tensor_list:
                        controls = []
                        for control_img in control_tensor_list:
                            # control images are 0-1. Dataloader already aligned
                            # control1 to the target bucket and left control2+ native.
                            control_img = control_img.to(
                                self.device_torch, dtype=self.torch_dtype
                            )
                            if len(control_img.shape) == 3:
                                control_img = control_img.unsqueeze(0)
                            control_img = control_img * 2 - 1
                            controls.append(control_img)

                        limit_pixels_list = [
                            (
                                target_pixels
                                if (sub_idx == 0 and match_target_res)
                                else 1024 * 1024
                            )
                            for sub_idx in range(len(controls))
                        ]

                        if self.vae.device == torch.device("cpu"):
                            self.vae.to(self.device_torch)
                        img_cond_seq_item, img_cond_seq_ids_item = encode_image_refs(
                            self.vae, controls, limit_pixels=limit_pixels_list
                        )
                        if img_cond_seq is None:
                            img_cond_seq = img_cond_seq_item
                            img_cond_seq_ids = img_cond_seq_ids_item
                        else:
                            img_cond_seq = torch.cat(
                                (img_cond_seq, img_cond_seq_item), dim=0
                            )
                            img_cond_seq_ids = torch.cat(
                                (img_cond_seq_ids, img_cond_seq_ids_item), dim=0
                            )

            img_input = packed_latents
            img_input_ids = img_ids

            if img_cond_seq is not None:
                assert img_cond_seq_ids is not None, (
                    "You need to provide either both or neither of the sequence conditioning"
                )
                img_input = torch.cat(
                    (img_input, img_cond_seq.to(img_input.device, img_input.dtype)), dim=1
                )
                img_input_ids = torch.cat(
                    (img_input_ids, img_cond_seq_ids.to(img_input_ids.device)), dim=1
                )

            guidance_vec = torch.full(
                (img_input.shape[0],),
                guidance_embedding_scale,
                device=img_input.device,
                dtype=img_input.dtype,
            )

            cast_dtype = self.model.dtype

        def _prep(t: torch.Tensor, dtype=cast_dtype) -> torch.Tensor:
            if dtype is not None:
                t = t.to(self.device_torch, dtype)
            else:
                t = t.to(self.device_torch)
            return t.clone()

        packed_noise_pred = self.transformer(
            x=_prep(img_input),
            x_ids=_prep(img_input_ids, dtype=None),
            timesteps=_prep(timestep) / 1000,
            ctx=_prep(txt),
            ctx_ids=_prep(txt_ids, dtype=None),
            guidance=_prep(guidance_vec),
        )

        if img_cond_seq is not None:
            packed_noise_pred = packed_noise_pred[:, : packed_latents.shape[1]]

        if isinstance(packed_noise_pred, QTensor):
            packed_noise_pred = packed_noise_pred.dequantize()

        noise_pred = torch.cat(scatter_ids(packed_noise_pred, img_ids)).squeeze(2)

        return noise_pred

    def get_prompt_embeds(self, prompt: str) -> PromptEmbeds:
        if self.pipeline.text_encoder.device != self.device_torch:
            self.pipeline.text_encoder.to(self.device_torch)

        prompt_embeds, prompt_embeds_mask = self.pipeline.encode_prompt(
            prompt, device=self.device_torch
        )
        pe = PromptEmbeds(prompt_embeds)
        return pe

    def get_model_has_grad(self):
        return False

    def get_te_has_grad(self):
        return False

    def save_model(self, output_path, meta, save_dtype):
        if not output_path.endswith(".safetensors"):
            output_path = output_path + ".safetensors"
        # only save the unet
        transformer: Flux2 = unwrap_model(self.model)
        state_dict = transformer.state_dict()
        save_dict = {}
        for k, v in state_dict.items():
            if isinstance(v, QTensor):
                v = v.dequantize()
            save_dict[k] = v.clone().to("cpu", dtype=save_dtype)

        meta = get_meta_for_safetensors(meta, name="flux2")
        save_file(save_dict, output_path, metadata=meta)

    def get_loss_target(self, *args, **kwargs):
        noise = kwargs.get("noise")
        batch = kwargs.get("batch")
        return (noise - batch.latents).detach()

    def get_base_model_version(self):
        return "flux2"

    def get_transformer_block_names(self) -> Optional[List[str]]:
        return ["double_blocks", "single_blocks"]

    lora_keys_use_comfy_prefix = True

    def encode_images(self, image_list: List[torch.Tensor], device=None, dtype=None):
        if device is None:
            device = self.vae_device_torch
        if dtype is None:
            dtype = self.vae_torch_dtype

        # Move to vae to device if on cpu
        if self.vae.device == torch.device("cpu"):
            self.vae.to(device)
        # move to device and dtype
        image_list = [image.to(device, dtype=dtype) for image in image_list]
        images = torch.stack(image_list).to(device, dtype=dtype)

        latents = self.vae.encode(images)

        return latents

    def encode_control_for_cache(
        self,
        control_tensor: torch.Tensor,
        control_index: int = 0,
        target_height: int | None = None,
        target_width: int | None = None,
    ) -> torch.Tensor:
        """Encode one control image tensor [0, 1] into a VAE latent (C, H, W).

        control1 optionally uses the target crop pixel count when match_target_res
        is set. control2+ always cap at 1024**2. Matches the live forward path.
        """
        with torch.no_grad():
            if self.vae.device == torch.device("cpu"):
                self.vae.to(self.device_torch)
            img = control_tensor.clone()
            if img.dim() == 4:
                img = img.squeeze(0)
            img = img * 2 - 1

            match_target_res = self.model_config.model_kwargs.get(
                "match_target_res", False
            )
            if (
                control_index == 0
                and match_target_res
                and target_height is not None
                and target_width is not None
            ):
                limit_pixels = int(target_height) * int(target_width)
            else:
                limit_pixels = 1024 * 1024

            img = default_prep(img, limit_pixels=limit_pixels)
            if img.dim() == 3:
                img = img.unsqueeze(0)
            encoded = self.vae.encode(img.to(self.vae.device, self.vae.dtype))[0]
            return encoded.detach().cpu()

    def decode_latents(self, latents, device=None, dtype=None):
        if device is None:
            device = self.vae_device_torch
        if dtype is None:
            dtype = self.vae_torch_dtype

        # Move to vae to device if on cpu
        if self.vae.device == torch.device("cpu"):
            self.vae.to(device)
        latents = latents.to(device, dtype=dtype)

        images = self.vae.decode(latents)

        return images
