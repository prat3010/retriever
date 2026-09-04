"""Production BentoML Serverless vLLM & LoRA Serving Service (M96).

Packages a high-performance vLLM engine with BentoML for deployment on BentoCloud
or Kubernetes (Yatai) with automatic scale-to-zero and dynamic tenant LoRA support.

Deploy command:
    bentoml build -f deploy/bentoml/bentofile.yaml
    bentoml deploy retriever_vllm_service:latest
"""

import os
from typing import AsyncGenerator

import bentoml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

BASE_MODEL = os.environ.get("BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
MAX_LORAS = int(os.environ.get("MAX_LORAS", "16"))


@bentoml.service(
    name="retriever-vllm-service",
    resources={"gpu": 1, "gpu_type": "nvidia-a10g"},
    traffic={"timeout": 600, "max_concurrency": 32},
    workers=1,
)
class RetrieverVllmService:
    """BentoML service encapsulating vLLM engine with Multi-LoRA support."""

    def __init__(self) -> None:
        from vllm.engine.arg_utils import AsyncEngineArgs
        from vllm.engine.async_llm_engine import AsyncLLMEngine

        engine_args = AsyncEngineArgs(
            model=BASE_MODEL,
            enable_lora=True,
            max_loras=MAX_LORAS,
            gpu_memory_utilization=0.90,
            trust_remote_code=True,
        )
        self.engine = AsyncLLMEngine.from_engine_args(engine_args)

    @bentoml.api
    async def health(self) -> dict[str, str]:
        return {"status": "healthy", "engine": "vllm", "base_model": BASE_MODEL}

    @bentoml.mount_asgi_app
    def get_api_app(self) -> FastAPI:
        web_app = FastAPI(title="BentoML vLLM OpenAI API", version="0.81.0")

        @web_app.post("/v1/chat/completions")
        async def chat_completions(request: Request):
            import json
            import time
            from vllm.lora.request import LoRARequest
            from vllm.sampling_params import SamplingParams

            body = await request.json()
            messages = body.get("messages", [])
            stream = body.get("stream", False)
            target_model = body.get("model", BASE_MODEL)

            lora_req: LoRARequest | None = None
            if ":" in target_model:
                _, lora_id = target_model.split(":", 1)
                lora_path = f"/models/loras/{lora_id}"
                if os.path.exists(lora_path):
                    lora_req = LoRARequest(
                        lora_name=lora_id,
                        lora_int_id=abs(hash(lora_id)) % 10000,
                        lora_path=lora_path,
                    )

            prompt_parts = [f"<|im_start|>{m.get('role', 'user')}\n{m.get('content', '')}<|im_end|>" for m in messages]
            prompt_parts.append("<|im_start|>assistant\n")
            full_prompt = "\n".join(prompt_parts)

            sampling_params = SamplingParams(
                temperature=float(body.get("temperature", 0.7)),
                max_tokens=int(body.get("max_tokens", 1024)),
                stop=["<|im_end|>", "<|endoftext|>"],
            )
            request_id = f"bento-{int(time.time() * 1000)}"

            results_gen = self.engine.generate(
                full_prompt, sampling_params, request_id=request_id, lora_request=lora_req
            )

            if stream:
                async def event_generator() -> AsyncGenerator[str, None]:
                    prev = ""
                    async for out in results_gen:
                        txt = out.outputs[0].text
                        delta = txt[len(prev):]
                        prev = txt
                        chunk = {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "model": target_model,
                            "choices": [{"delta": {"content": delta}, "finish_reason": out.outputs[0].finish_reason}],
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                    yield "data: [DONE]\n\n"

                return StreamingResponse(event_generator(), media_type="text/event-stream")

            final_out = None
            async for out in results_gen:
                final_out = out

            if final_out is None:
                raise HTTPException(status_code=500, detail="Generation failed")

            return JSONResponse({
                "id": request_id,
                "object": "chat.completion",
                "model": target_model,
                "choices": [{"message": {"role": "assistant", "content": final_out.outputs[0].text}}],
                "usage": {
                    "prompt_tokens": len(final_out.prompt_token_ids),
                    "completion_tokens": len(final_out.outputs[0].token_ids),
                    "total_tokens": len(final_out.prompt_token_ids) + len(final_out.outputs[0].token_ids),
                },
            })

        return web_app
