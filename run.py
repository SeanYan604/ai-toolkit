import os
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
os.environ["NO_ALBUMENTATIONS_UPDATE"] = "1"
os.environ["HF_HOME"] = "/root/autodl-tmp/pretrained_models"
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

if os.name == 'nt':
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "backend:cudaMallocAsync")

import sys
from typing import Union, OrderedDict
from dotenv import load_dotenv
# Load the .env file if it exists
load_dotenv()

sys.path.insert(0, os.getcwd())
# must come before ANY torch or fastai imports
# import toolkit.cuda_malloc

# turn off diffusers telemetry until I can figure out how to make it opt-in
os.environ['DISABLE_TELEMETRY'] = 'YES'

# check if we have DEBUG_TOOLKIT in env
if os.environ.get("DEBUG_TOOLKIT", "0") == "1":
    # set torch to trace mode
    import torch
    torch.autograd.set_detect_anomaly(True)
import argparse
from toolkit.job import get_job
from toolkit.accelerator import get_accelerator
from toolkit.print import print_acc, setup_log_to_file

accelerator = get_accelerator()

import torch
if torch.cuda.is_available():
    def _select_best_sdp_backend():
        """Auto-select the fastest SDPA backend for this GPU."""
        try:
            from torch.nn.attention import sdpa_kernel, SDPBackend
            q = torch.randn(1, 8, 256, 64, dtype=torch.bfloat16, device='cuda')
            k = torch.randn(1, 8, 256, 64, dtype=torch.bfloat16, device='cuda')
            v = torch.randn(1, 8, 256, 64, dtype=torch.bfloat16, device='cuda')
            candidates = [
                ("cudnn", SDPBackend.CUDNN_ATTENTION),
                ("flash", SDPBackend.FLASH_ATTENTION),
            ]
            best_name, best_ms = None, float('inf')
            import time
            for name, backend in candidates:
                try:
                    with sdpa_kernel(backend):
                        for _ in range(3):
                            torch.nn.functional.scaled_dot_product_attention(q, k, v)
                        torch.cuda.synchronize()
                        t0 = time.perf_counter()
                        for _ in range(10):
                            torch.nn.functional.scaled_dot_product_attention(q, k, v)
                        torch.cuda.synchronize()
                        ms = (time.perf_counter() - t0) / 10 * 1000
                        if ms < best_ms:
                            best_name, best_ms = name, ms
                except Exception:
                    pass
            del q, k, v
            torch.cuda.empty_cache()
            # Always keep math enabled as universal fallback (VAE, etc.)
            torch.backends.cuda.enable_math_sdp(True)
            if best_name == "cudnn":
                torch.backends.cuda.enable_cudnn_sdp(True)
                torch.backends.cuda.enable_flash_sdp(False)
                torch.backends.cuda.enable_mem_efficient_sdp(False)
                print_acc(f"[perf] Preferred SDPA backend: cuDNN ({best_ms:.2f}ms)")
            elif best_name == "flash":
                torch.backends.cuda.enable_cudnn_sdp(False)
                torch.backends.cuda.enable_flash_sdp(True)
                torch.backends.cuda.enable_mem_efficient_sdp(False)
                print_acc(f"[perf] Preferred SDPA backend: Flash ({best_ms:.2f}ms)")
            else:
                print_acc("[perf] Keeping default SDPA backend selection")
        except Exception as e:
            print_acc(f"[perf] SDPA auto-select skipped: {e}")

    _select_best_sdp_backend()
    del _select_best_sdp_backend


def print_end_message(jobs_completed, jobs_failed):
    if not accelerator.is_main_process:
        return
    failure_string = f"{jobs_failed} failure{'' if jobs_failed == 1 else 's'}" if jobs_failed > 0 else ""
    completed_string = f"{jobs_completed} completed job{'' if jobs_completed == 1 else 's'}"

    print_acc("")
    print_acc("========================================")
    print_acc("Result:")
    if len(completed_string) > 0:
        print_acc(f" - {completed_string}")
    if len(failure_string) > 0:
        print_acc(f" - {failure_string}")
    print_acc("========================================")


def main():
    parser = argparse.ArgumentParser()

    # require at lease one config file
    parser.add_argument(
        'config_file_list',
        nargs='+',
        type=str,
        help='Name of config file (eg: person_v1 for config/person_v1.json/yaml), or full path if it is not in config folder, you can pass multiple config files and run them all sequentially'
    )

    # flag to continue if failed job
    parser.add_argument(
        '-r', '--recover',
        action='store_true',
        help='Continue running additional jobs even if a job fails'
    )

    # flag to continue if failed job
    parser.add_argument(
        '-n', '--name',
        type=str,
        default=None,
        help='Name to replace [name] tag in config file, useful for shared config file'
    )
    
    parser.add_argument(
        '-l', '--log',
        type=str,
        default=None,
        help='Log file to write output to'
    )
    args = parser.parse_args()
    
    if args.log is not None:
        setup_log_to_file(args.log)

    config_file_list = args.config_file_list
    if len(config_file_list) == 0:
        raise Exception("You must provide at least one config file")

    jobs_completed = 0
    jobs_failed = 0

    if accelerator.is_main_process:
        print_acc(f"Running {len(config_file_list)} job{'' if len(config_file_list) == 1 else 's'}")

    for config_file in config_file_list:
        try:
            job = get_job(config_file, args.name)
            job.run()
            job.cleanup()
            jobs_completed += 1
        except Exception as e:
            sys.stdout.flush()
            sys.stderr.flush()
            print_acc(f"Error running job: {e}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            sys.stderr.flush()
            jobs_failed += 1
            try:
                job.process[0].on_error(e)
            except Exception as e2:
                print_acc(f"Error running on_error: {e2}")
            if not args.recover:
                print_end_message(jobs_completed, jobs_failed)
                raise e
        except KeyboardInterrupt as e:
            try:
                job.process[0].on_error(e)
            except Exception as e2:
                print_acc(f"Error running on_error: {e2}")
            if not args.recover:
                print_end_message(jobs_completed, jobs_failed)
                raise e


if __name__ == '__main__':
    main()
