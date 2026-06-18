from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache


class Settings(BaseSettings):
    # Server
    port: int = 3000
    env: str = "development"

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_auto_provision: bool = False

    # Deepgram
    deepgram_api_key: str = ""
    deepgram_model: str = "nova-3"
    deepgram_endpointing_ms: int = 650  # ms silence before STT fires is_final

    # Cartesia
    cartesia_api_key: str = ""
    cartesia_voice_id: str = ""
    cartesia_model: str = "sonic-2"

    # Anthropic
    anthropic_api_key: str = ""
    # Haiku: fast + cheap for voice turns. Swap to sonnet for complex reasoning.
    anthropic_model: str = "claude-haiku-4-5"
    anthropic_max_tokens: int = 200

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Redis
    redis_url: str = ""

    # OpenAI (used only for KB embeddings via text-embedding-3-small)
    openai_api_key: str = ""

    # Escalation — phone number to warm-transfer to when Claude escalates
    escalation_phone: str = ""

    # Public base URL used to build Twilio callback URLs (e.g. https://xxx.ngrok-free.app)
    base_url: str = ""

    # Email (Resend)
    resend_api_key: str = ""
    email_from: str = "Turboman <noreply@turboman.ca>"
    frontend_url: str = "http://localhost:3000"

    # Error monitoring
    sentry_dsn: str = ""

    # CORS — comma-separated list of allowed origins (override via CORS_ORIGINS env var)
    cors_origins: str = "http://localhost:3000,https://turboman.ca,https://www.turboman.ca,https://app.turboman.ca"

    # Admin API — secret header required for privileged routes (e.g. POST /auth/users)
    admin_secret: str = ""

    # Dashboard auth
    jwt_secret: str = "change-me-in-production"

    # Call behaviour
    silence_reprompt_ms: int = 8000    # silence after AI finishes before first reprompt
    max_reprompts: int = 2              # after 2 unanswered reprompts, end the call
    transcript_debounce_ms: int = 100   # wait after last is_final before processing

    @model_validator(mode="after")
    def check_required(self):
        required = [
            ("TWILIO_ACCOUNT_SID", self.twilio_account_sid),
            ("TWILIO_AUTH_TOKEN", self.twilio_auth_token),
            ("DEEPGRAM_API_KEY", self.deepgram_api_key),
            ("ANTHROPIC_API_KEY", self.anthropic_api_key),
            ("SUPABASE_URL", self.supabase_url),
            ("SUPABASE_SERVICE_ROLE_KEY", self.supabase_service_role_key),
            ("REDIS_URL", self.redis_url),
        ]
        missing = [name for name, val in required if not val]
        if missing and self.env == "production":
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")
        if self.env == "production" and self.jwt_secret == "change-me-in-production":
            raise ValueError("JWT_SECRET must be changed from the default before running in production")
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Convenience alias
settings = get_settings()
