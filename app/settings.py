from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_prefix: str = "/api/v1"

    ollama_model: str = "qwen3.5:4b"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_api_key: str = "ollama"
    ollama_timeout: float = 300.0
    ollama_temperature: float = 0.0
    ollama_reasoning_effort: str = "none"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_timeout: float = 10.0
    mail_from: str = "message-router@example.com"

    message_max_length: int = 2000
    agent_retries: int = 1


settings = Settings()
