from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    postgres_user: str = "otto"
    postgres_password: str = ""
    postgres_db: str = "memory"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""

    # OpenAI (used for embeddings)
    openai_api_key: str = ""

    # Gemini (used for Otto's LLM responses)
    gemini_api_key: str = ""

    # Graphiti
    graphiti_url: str = "http://localhost:8000"

    # WhatsApp
    whatsapp_url: str = "http://localhost:3001"

    # Neo4j (for reference)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # Focus context compression (arXiv 2601.07190)
    # If assembled context exceeds this token count, apply rule-based compression
    context_compression_threshold: int = 4000
    # Target token count after compression (hard ceiling)
    context_max_tokens: int = 5000

    # SVC: Singular Value Calibration for embedding quality (sweep #13)
    # Removes top-k principal components (bias directions) from query embeddings
    # to reduce anisotropy and improve semantic retrieval accuracy.
    svc_enabled: bool = True
    svc_top_k: int = 3
    svc_components_path: str = "/home/web3relic/otto/memory/svc_components.npz"

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = {"env_file": "/home/web3relic/memory/.env", "extra": "ignore"}


settings = Settings()
