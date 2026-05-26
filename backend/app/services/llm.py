from typing import Any

import httpx

from app.schemas.media import LLMModelRead


class LLMService:
    async def list_models(self, api_base_url: str, api_key: str = "") -> list[LLMModelRead]:
        base_url = api_base_url.rstrip("/")
        if not base_url:
            raise ValueError("LLM API Base URL 不能为空")

        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{base_url}/models", headers=headers)
            response.raise_for_status()
            payload = response.json()

        models = self._extract_models(payload)
        return sorted(models, key=lambda model: model.id.lower())

    def _extract_models(self, payload: Any) -> list[LLMModelRead]:
        if isinstance(payload, dict):
            data = payload.get("data", [])
        elif isinstance(payload, list):
            data = payload
        else:
            data = []

        models: list[LLMModelRead] = []
        for item in data:
            if isinstance(item, str):
                models.append(LLMModelRead(id=item))
            elif isinstance(item, dict) and item.get("id"):
                owned_by = item.get("owned_by")
                models.append(LLMModelRead(id=str(item["id"]), owned_by=str(owned_by) if owned_by else None))
        return models
