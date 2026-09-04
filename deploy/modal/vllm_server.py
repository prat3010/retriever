"""Production Serverless vLLM & Multi-LoRA Serving Recipe for Modal (M96).

Deploys an OpenAI-compatible vLLM inference server on serverless GPUs with:
1. Scale-to-Zero auto-scaling: scales down to 0 instances after idle timeout (default 300s).
2. Dynamic Multi-LoRA runtime loading: loads tenant LoRA weights dynamically without restarts.
3. High-throughput PagedAttention with CUDA hardware acceleration.

Deploy command:
    modal deploy deploy/modal/vllm_server.py
"""

import os
from typing import Any

import modal

# Modal application configuration
APP_NAME = "retriever-vllm-serving"
BASE_MODEL = os.environ.get("BASE_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")
GPU_SPEC = os.environ.get("MODAL_GPU", "A10G")  # Options: A10G, L4, A100
SCALEDOWN_WINDOW = int(os.environ.get("SCALEDOWN_WINDOW", "300"))  # 5 minutes idle to 0
MAX_LORAS = int(os.environ.get("MAX_LORAS", "16"))
MAX_LORA_RANK = int(os.environ.get("MAX_LORA_RANK", "64"))

# Persistent Volume for model weights and LoRA cache
model_volume = modal.Volume.from_name("retriever-model-cache", create_if_missing=True)
lora_volume = modal.Volume.from_name("retriever-lora-vault", create_if_missing=True)

# Container Image with CUDA, vLLM, and PyTorch
vllm_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "vllm>=0.6.0",
        "torch>=2.4.0",
        "transformers>=4.44.0",
        "accelerate>=0.33.0",
        "peft>=0.12.0",
        "huggingface_hub>=0.24.0",
        "fastapi>=0.110.0",
        "uvicorn>=0.28.0",
        "pydantic>=2.6.0",
        "httpx>=0.27.0",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

app = modal.App(APP_NAME, image=vllm_image)


@app.function(
    volumes={"/root/.cache/huggingface": model_volume, "/root/loras": lora_volume},
    secrets=[modal.Secret.from_name("huggingface-secret", required=False)],
    timeout=1800,
)
def download_model(model_name: str = BASE_MODEL) -> None:
    """Pre-cache base model weights into the persistent volume."""
    from huggingface_hub import snapshot_download

    print(f"Downloading base model weights for {model_name}...")
    snapshot_download(repo_id=model_name, local_files_only=False)
    model_volume.commit()
    print("Base model weights cached successfully.")


@app.function(
    image=vllm_image,
    gpu=modal.gpu.A10G(count=1),
    scaledown_window=SCALEDOWN_WINDOW,
    timeout=600,
    allow_concurrent_inputs=32,
    volumes={"/root/.cache/huggingface": model_volume, "/root/loras": lora_volume},
    secrets=[modal.Secret.from_name("huggingface-secret", required=False)],
)
@modal.asgi_app()
def serve_vllm() -> Any:
    """ASGI entrypoint serving OpenAI-compatible chat completions with dynamic LoRA."""
    import json
    import time
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse, StreamingResponse
    from vllm.engine.arg_utils import AsyncEngineArgs
    from vllm.engine.async_llm_engine import AsyncLLMEngine
    from vllm.lora.request import LoRARequest
    from vllm.sampling_params import SamplingParams

    web_app = FastAPI(title="Retriever Serverless vLLM Serving", version="0.81.0")

    # Initialize Async vLLM Engine
    engine_args = AsyncEngineArgs(
        model=BASE_MODEL,
        enable_lora=True,
        max_loras=MAX_LORAS,
        max_lora_rank=MAX_LORA_RANK,
        gpu_memory_utilization=0.90,
        max_model_len=8192,
        trust_remote_code=True,
    )
    engine = AsyncLLMEngine.from_engine_args(engine_args)
    boot_time = time.time()

    @web_app.get("/health")
    async def health_check() -> dict[str, Any]:
        """Health check endpoint sensing container lifecycle."""
        return {
            "status": "healthy",
            "base_model": BASE_MODEL,
            "gpu": GPU_SPEC,
            "uptime_seconds": round(time.time() - boot_time, 2),
            "max_loras": MAX_LORAS,
        }

    @web_app.get("/v1/models")
    async def list_models() -> dict[str, Any]:
        """OpenAI-compatible models listing."""
        return {
            "object": "list",
            "data": [
                {
                    "id": BASE_MODEL,
                    "object": "model",
                    "created": int(boot_time),
                    "owned_by": "retriever-serverless",
                }
            ],
        }

    @web_app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> Any:
        """OpenAI-compatible chat completions endpoint with dynamic LoRA resolution."""
        body = await request.json()
        messages = body.get("messages", [])
        if not messages:
            raise HTTPException(status_code=400, detail="Messages list cannot be empty")

        stream = body.get("stream", False)
        temperature = float(body.get("temperature", 0.7))
        max_tokens = int(body.get("max_tokens", 1024))
        target_model = body.get("model", BASE_MODEL)

        # Dynamic LoRA adapter resolution
        # Format can be: "base_model:adapter_name" or passed via header 'x-lora-path'
        lora_req: LoRARequest | None = None
        custom_lora_path = request.headers.get("x-lora-artifact-uri")
        custom_lora_id = request.headers.get("x-lora-id")

        if ":" in target_model:
            _, lora_name = target_model.split(":", 1)
            lora_path = f"/root/loras/{lora_name}"
            if os.path.exists(lora_path):
                lora_req = LoRARequest(lora_name=lora_name, lora_int_id=abs(hash(lora_name)) % 10000, lora_path=lora_path)
        elif custom_lora_path and custom_lora_id:
            lora_req = LoRARequest(
                lora_name=custom_lora_id,
                lora_int_id=abs(hash(custom_lora_id)) % 10000,
                lora_path=custom_lora_path,
            )

        # Build prompt from messages
        prompt_parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            prompt_parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
        prompt_parts.append("<|im_start|>assistant\n")
        full_prompt = "\n".join(prompt_parts)

        request_id = f"chatcmpl-{int(time.time() * 1000)}"
        sampling_params = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            stop=["<|im_end|>", "<|endoftext|>"],
        )

        results_generator = engine.generate(
            full_prompt,
            sampling_params,
            request_id=request_id,
            lora_request=lora_req,
        )

        if stream:
            async def event_generator():
                prev_text = ""
                async for output in results_generator:
                    current_text = output.outputs[0].text
                    delta = current_text[len(prev_text):]
                    prev_text = current_text
                    chunk = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": target_model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": delta},
                                "finish_reason": output.outputs[0].finish_reason,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")

        # Synchronous completion
        final_output = None
        async for output in results_generator:
            final_output = output

        if final_output is None:
            raise HTTPException(status_code=500, detail="Inference produced no output")

        generated_text = final_output.outputs[0].text
        prompt_tokens = len(final_output.prompt_token_ids) if final_output.prompt_token_ids else 0
        completion_tokens = len(final_output.outputs[0].token_ids) if final_output.outputs[0].token_ids else 0

        return JSONResponse({
            "id": request_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": target_model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": generated_text},
                    "finish_reason": final_output.outputs[0].finish_reason or "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        })

    return web_app
