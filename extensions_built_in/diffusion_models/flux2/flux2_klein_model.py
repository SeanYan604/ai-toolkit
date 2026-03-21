import os
from .flux2_model import Flux2Model
from transformers import Qwen3ForCausalLM, Qwen2Tokenizer
from optimum.quanto import freeze
from toolkit.util.quantize import quantize, get_qtype
from toolkit.config_modules import ModelConfig
from toolkit.memory_management.manager import MemoryManager
from toolkit.basic import flush
from .src.model import Klein9BParams, Klein4BParams


class Flux2KleinModel(Flux2Model):
    flux2_klein_te_path: str = None
    flux2_te_type: str = "qwen"  # "mistral" or "qwen"
    flux2_vae_path: str = "ai-toolkit/flux2_vae"
    flux2_is_guidance_distilled: bool = False

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
            device,
            model_config,
            dtype,
            custom_pipeline,
            noise_scheduler,
            **kwargs,
        )
        # use the new format on this new model by default
        self.use_old_lokr_format = False

    def _resolve_te_path(self):
        """
        Resolve the text encoder path with the following priority:
        1. model_kwargs.te_path (explicit local path from config)
        2. Auto-detect: sibling directory of name_or_path (e.g. pretrained_models/qwen3_8b)
        3. self.flux2_klein_te_path (class default, e.g. "Qwen/Qwen3-8B" from HF Hub)
        """
        # 1. Check model_kwargs for explicit local te_path
        te_path = self.model_config.model_kwargs.get("te_path", None)
        if te_path and os.path.isdir(te_path):
            return te_path

        # 2. Auto-detect: look for qwen3_8b/qwen3_4b next to the model directory
        model_path = self.model_config.name_or_path
        if model_path and os.path.isdir(model_path):
            parent_dir = os.path.dirname(model_path)
            te_dir_name = "qwen3_8b" if "8B" in (self.flux2_klein_te_path or "") else "qwen3_4b"
            local_te = os.path.join(parent_dir, te_dir_name)
            if os.path.isdir(local_te):
                return local_te

        # 3. Fallback to class default (HF Hub)
        if self.flux2_klein_te_path is None:
            raise ValueError("flux2_klein_te_path must be set for Flux2KleinModel")
        return self.flux2_klein_te_path

    def load_te(self):
        te_path = self._resolve_te_path()
        dtype = self.torch_dtype
        self.print_and_status_update(f"Loading Qwen3 from {te_path}")

        text_encoder: Qwen3ForCausalLM = Qwen3ForCausalLM.from_pretrained(
            te_path,
            torch_dtype=dtype,
        )
        text_encoder.to(self.device_torch, dtype=dtype)

        flush()

        if self.model_config.quantize_te:
            self.print_and_status_update("Quantizing Qwen3")
            quantize(text_encoder, weights=get_qtype(self.model_config.qtype))
            freeze(text_encoder)
            flush()

        if (
            self.model_config.layer_offloading
            and self.model_config.layer_offloading_text_encoder_percent > 0
        ):
            MemoryManager.attach(
                text_encoder,
                self.device_torch,
                offload_percent=self.model_config.layer_offloading_text_encoder_percent,
            )

        tokenizer = Qwen2Tokenizer.from_pretrained(te_path)
        return text_encoder, tokenizer


class Flux2Klein4BModel(Flux2KleinModel):
    arch = "flux2_klein_4b"
    flux2_klein_te_path: str = "Qwen/Qwen3-4B"
    flux2_te_filename: str = "flux-2-klein-base-4b.safetensors"

    def get_flux2_params(self):
        return Klein4BParams()

    def get_base_model_version(self):
        return "flux2_klein_4b"


class Flux2Klein9BModel(Flux2KleinModel):
    arch = "flux2_klein_9b"
    flux2_klein_te_path: str = "Qwen/Qwen3-8B"
    flux2_te_filename: str = "flux-2-klein-base-9b.safetensors"

    def get_flux2_params(self):
        return Klein9BParams()

    def get_base_model_version(self):
        return "flux2_klein_9b"
