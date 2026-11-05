from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str

    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 day default for convenience
    reset_token_expire_minutes: int = 60

    # S3 Configuration
    s3_bucket_name: str = "baseproject-media"
    s3_region: str = "us-east-1"
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_endpoint_url: str | None = None

    # S3-compatible object storage (e.g., Neon / Custom S3)
    aws_endpoint_url_s3: str | None = None
    aws_access_key_id: SecretStr | None = None
    aws_secret_access_key: SecretStr | None = None
    aws_region: str = "us-east-2"

    max_upload_size_bytes: int = 5 * 1024 * 1024

    # Databricks Connector Defaults
    databricks_host: str | None = None
    databricks_token: SecretStr | None = None

    # FalkorDB Graph Database
    falkordb_url: str = "falkordb://localhost:6379"
    falkordb_graph_name: str = "enterprise_knowledge_graph"

    # Qdrant Vector Database
    qdrant_url: str | None = None
    qdrant_api_key: SecretStr | None = None
    qdrant_collection_name: str = "databricks_knowledge_chunks"

    # Storage & Embeddings
    storage_provider: str = "s3"
    storage_bucket: str = "uploads"
    embedding_provider: str = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384

    # Groq LLM Configuration
    groq_api_key_1: SecretStr | None = None
    groq_api_key_2: SecretStr | None = None
    groq_api_key_3: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_api_base: str = "https://api.groq.com/openai/v1"

    # Hugging Face Configuration (LAnoBERT)
    huggingface_api_key: SecretStr | None = None
    hf_token: SecretStr | None = None

    # Email server configurations
    mail_server: str = "localhost"
    mail_port: int = 587
    mail_username: str = ""
    mail_password: SecretStr = SecretStr("")
    mail_from: str = "noreply@example.com"
    mail_use_tls: bool = True

    frontend_url: str = "http://localhost:3000"


settings = Settings()  # type: ignore[call-arg]

