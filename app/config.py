from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 8080
    log_level: str = "info"

    # RabbitMQ
    rabbitmq_url: str

    # OpenAI
    openai_api_key: str
    extract_model: str = "gpt-5-mini"
    vision_model: str = "gpt-5"

    # Service URLs
    dictionary_url: str = "http://woodpantry-ingredients:8080"
    recipe_url: str = "http://woodpantry-recipes:8080"
    pantry_url: str | None = None  # Optional — W-2 not complete yet

    # Twilio (optional — W-5 scope)
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None

    model_config = {"env_prefix": ""}

    @property
    def twilio_signature_validation_enabled(self) -> bool:
        return bool(self.twilio_auth_token)

    @property
    def twilio_outbound_enabled(self) -> bool:
        return bool(
            self.twilio_account_sid
            and self.twilio_auth_token
            and self.twilio_from_number
        )


settings = Settings()
