from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # VAPI
    vapi_api_key: str = ""
    vapi_assistant_id: str = ""
    vapi_phone_number_id: str = ""
    vapi_secret: str = ""

    # n8n Cloud
    n8n_api_key: str = ""
    n8n_webhook_base_url: str = ""

    # FastAPI
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
