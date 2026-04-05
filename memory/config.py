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

    # BANKR Bot integration (legacy — kept for reference, replaced by native crypto engine)
    bankr_api_key: str = ""                    # bk_... key from bankr.bot dashboard
    bankr_enabled: bool = False                # master feature flag (requires API key)
    bankr_signals_enabled: bool = False        # publish signals to bankrsignals.com
    bankr_llm_gateway_enabled: bool = False    # Phase 3 only — LLM cost routing
    bankr_api_url: str = "https://api.bankr.bot"
    bankr_signals_url: str = "https://api.bankrsignals.com"
    bankr_job_poll_timeout: int = 30           # seconds to poll inline before queuing
    bankr_job_poll_interval: float = 2.0       # seconds between polls

    # ── Native Crypto Engine (replaces Bankr integration) ─────────────
    crypto_enabled: bool = False               # Master feature flag
    crypto_execution_enabled: bool = False     # Enables actual trade execution (set True only after key review)
    alchemy_api_key: str = ""                  # For EVM balance queries (Base, ETH, Polygon)
    zerox_api_key: str = ""                    # Optional — improves 0x rate limits
    coingecko_api_key: str = ""               # Optional — removes CoinGecko rate limits
    birdeye_api_key: str = ""                  # Optional — Solana token data
    zerox_api_url: str = "https://api.0x.org"  # 0x Swap API base URL
    cdp_api_key_name: str = ""                 # CDP AgentKit key name (Phase 2 execution)
    cdp_api_key_private_key: str = ""          # CDP AgentKit private key (Phase 2 execution)

    # ── Koink Standard integration ────────────────────────────────────
    koink_enabled: bool = False        # Master feature flag — enable after Phase 1 wallet setup

    # ── ONEON Identity Network ─────────────────────────────────────────
    oneon_enabled: bool = False        # Master feature flag — Phase 0 available now
    oneon_vault_master_key: str = ""   # AES-256-GCM key for session key encryption (Fernet-compatible)
    oneon_base_rpc_url: str = "https://mainnet.base.org"  # Base L2 RPC (Phase 1B)
    oneon_factory_address: str = ""    # Smart account factory contract (Phase 1B)
    oneon_paymaster_address: str = ""  # Paymaster contract (Phase 1B)
    oneon_magic_link_base_url: str = "https://oneon.ink/auth/verify"  # Magic link redirect

    # ── Tusita Community Locations ─────────────────────────────────────
    tusita_enabled: bool = False       # Master feature flag — Phase 0 available now

    # ── SOS Systems ────────────────────────────────────────────────────
    sos_enabled: bool = False          # Master feature flag — Phase 0 available now

    # ── Gate Notification System ──────────────────────────────────────
    gate_whatsapp_enabled: bool = True
    # Comma-separated list of webhook URLs to POST gate events to
    gate_webhook_urls: str = ""
    # Optional bearer token sent as Authorization: Bearer <token> in webhook POSTs
    gate_webhook_secret: str = ""

    # ── OpenTelemetry ────────────────────────────────────────────────
    otel_enabled: bool = False
    otel_service_name: str = "otto-memory-api"
    otel_environment: str = "production"  # deployment.environment tag
    otel_export_endpoint: str = ""  # OTLP endpoint (empty = file-only)
    otel_log_dir: str = "/home/web3relic/otto/logs/traces"
    otel_trace_retention_days: int = 30  # Auto-prune trace files older than this

    # ── MCP Server ───────────────────────────────────────────────────
    # Bearer token for external MCP clients. Empty = dev mode (no auth).
    mcp_token: str = ""

    # ── Secrets Vault ─────────────────────────────────────────────────
    # Fernet master key — ONLY secret that must stay in .env.
    # Generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Back this up separately — loss = all vault secrets unrecoverable.
    vault_master_key: str = ""

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = {"env_file": "/home/web3relic/memory/.env", "extra": "ignore"}


settings = Settings()
