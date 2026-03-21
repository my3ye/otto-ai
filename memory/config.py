from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    postgres_user: str = "otto"
    postgres_password: str = "changeme"
    postgres_db: str = "memory"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # OpenAI (used for semantic memory embeddings)
    openai_api_key: str = ""

    # Graphiti (temporal knowledge graph API)
    graphiti_url: str = "http://localhost:8000"

    # Neo4j (used by Graphiti internally)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
