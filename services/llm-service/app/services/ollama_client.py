import asyncio
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    pass


class OllamaUnavailableError(OllamaError):
    pass


class OllamaResponseError(OllamaError):
    pass


@dataclass(frozen=True)
class OllamaClient:
    base_url: str
    model: str
    timeout_seconds: float
    temperature: float
    max_tokens: int

    async def is_available(self) -> bool:
        response = await asyncio.to_thread(self._request_json, "/api/tags")
        models = response.get("models")
        return isinstance(models, list) and any(
            isinstance(model, dict)
            and (model.get("name") == self.model or model.get("model") == self.model)
            for model in models
        )

    async def generate(self, prompt: str, prompt_type: str) -> str:
        started = time.monotonic()
        try:
            response = await asyncio.to_thread(
                self._request_json,
                "/api/generate",
                {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    },
                },
            )
            generated = response.get("response")
            if not isinstance(generated, str) or not generated.strip():
                raise OllamaResponseError("Ollama returned an empty response")
            return generated
        finally:
            logger.info(
                "Ollama request finished prompt_type=%s model=%s latency_ms=%d",
                prompt_type,
                self.model,
                round((time.monotonic() - started) * 1000),
            )

    def _request_json(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="GET" if payload is None else "POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except TimeoutError as error:
            raise OllamaUnavailableError("Ollama request timed out") from error
        except urllib.error.HTTPError as error:
            raise OllamaResponseError(f"Ollama returned HTTP {error.code}") from error
        except (urllib.error.URLError, OSError) as error:
            raise OllamaUnavailableError("Ollama is unavailable") from error

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as error:
            raise OllamaResponseError("Ollama returned invalid JSON") from error
        if not isinstance(parsed, dict):
            raise OllamaResponseError("Ollama returned an invalid response object")
        return parsed
