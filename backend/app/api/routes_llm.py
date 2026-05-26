import httpx
from fastapi import APIRouter, HTTPException

from app.schemas.media import LLMModelsRead, LLMModelsRequest
from app.services.llm import LLMService

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/models", response_model=LLMModelsRead)
async def list_llm_models(payload: LLMModelsRequest) -> LLMModelsRead:
    try:
        models = await LLMService().list_models(payload.api_base_url, payload.api_key)
        return LLMModelsRead(models=models)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        detail = f"模型接口返回错误：HTTP {exc.response.status_code}"
        try:
            error_payload = exc.response.json()
            detail = error_payload.get("error", {}).get("message") or error_payload.get("detail") or detail
        except ValueError:
            pass
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"无法连接 LLM 端点：{exc}") from exc
