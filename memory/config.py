from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    postgres_user: str = "otto"
    postgres_password: str = ""
    postgres_db: str = "memory"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # OpenAI (used for embeddings)
    openai_api_key: str = ""

    # Gemini (used for Otto's LLM responses)
    gemini_api_key: str = ""

    # Kimi (primary LLM — replaces Gemini for conversational + internal tasks)
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.kimi.com/coding/v1"
    kimi_model: str = "kimi-for-coding"

    # Graphiti
    graphiti_url: str = "http://localhost:8000"

    # WhatsApp
    whatsapp_url: str = "http://localhost:3001"

    # Web interface auth
    web_auth_token: str = ""

    # WebAssist Supabase
    webassist_supabase_url: str = ""
    webassist_supabase_service_key: str = ""

    # Neo4j (for reference)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # Focus context compression (arXiv 2601.07190)
    # If assembled context exceeds this token count, apply rule-based compression
    context_compression_threshold: int = 20000
    # Target token count after compression (hard ceiling)
    context_max_tokens: int = 25000

    # SVC: Singular Value Calibration for embedding quality (sweep #13)
    # Removes top-k principal components (bias directions) from query embeddings
    # to reduce anisotropy and improve semantic retrieval accuracy.
    svc_enabled: bool = True
    svc_top_k: int = 3
    svc_components_path: str = "/home/web3relic/otto/memory/svc_components.npz"

    # ── AgentOS Kernel Settings (arXiv 2602.20934v1) ──────────────────
    # Feature flag: when False, gateway uses legacy direct-LLM path
    kernel_enabled: bool = True

    # S-MMU L1 capacity in tokens (always-resident ~2k + dynamic ~10k)
    l1_capacity_tokens: int = 12000

    # Cognitive drift threshold: Δψ > this triggers a Sync Pulse
    drift_threshold: float = 0.3

    # Measure drift every N interrupts
    drift_check_interval: int = 5

    # Interrupt processing timeout in seconds (120s to accommodate Claude Code CLI startup)
    interrupt_timeout_seconds: int = 120

    # Sync pulse interval in minutes (in addition to event-driven sync)
    sync_interval_minutes: int = 60

    # Investor page
    investor_password: str = "MY3YE2026"

    # Hyperliquid trading wallets
    otto_wallet_address: str = ""
    otto_wallet_private_key: str = ""
    otto_trading_wallet_address: str = ""
    otto_trading_wallet_private_key: str = ""
    hyperliquid_network: str = "mainnet"

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = {"env_file": "/home/web3relic/memory/.env", "extra": "ignore"}


settings = Settings()
