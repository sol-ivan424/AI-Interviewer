import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    llm_api_base_url: str = "https://api.openai.com"
    llm_api_key: str = field(default="", repr=False)
    llm_provider: str = "openai_compatible"
    ollama_base_url: str = "http://ollama:11434"
    llm_model: str = "gpt-4.1-mini"
    llm_timeout_seconds: float = 60
    llm_temperature: float = 0.2
    llm_max_tokens: int = 700

    def __post_init__(self) -> None:
        if not self.llm_api_base_url or not self.llm_provider or not self.llm_model:
            raise ValueError("LLM API base URL, provider and model must not be empty")
        if self.llm_timeout_seconds <= 0 or self.llm_max_tokens <= 0:
            raise ValueError("LLM timeout and max tokens must be positive")
        if not 0 <= self.llm_temperature <= 2:
            raise ValueError("LLM_TEMPERATURE must be between 0 and 2")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            llm_api_base_url=os.getenv("LLM_API_BASE_URL", cls.llm_api_base_url).rstrip("/"),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_provider=os.getenv("LLM_PROVIDER", cls.llm_provider),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", cls.ollama_base_url).rstrip("/"),
            llm_model=os.getenv("LLM_MODEL", cls.llm_model),
            llm_timeout_seconds=float(
                os.getenv("LLM_TIMEOUT_SECONDS", str(cls.llm_timeout_seconds))
            ),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", str(cls.llm_temperature))),
            llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", str(cls.llm_max_tokens))),
        )


settings = Settings.from_env()
