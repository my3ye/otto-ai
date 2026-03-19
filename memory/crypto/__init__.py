"""Native Crypto Engine — Otto's in-house implementation of crypto trading & DeFi features.

Modules:
    nlparser   — NL → TradeIntent (Claude-powered intent extraction)
    executor   — Trade execution via 0x Swap API + CDP AgentKit
    price_feed — Price data via CoinGecko (free) + Birdeye (Solana)
    portfolio  — Multi-chain balance + PnL aggregation
    monitors   — Conditional orders (limit/stop-loss/DCA) polling engine
    signals    — Native signal board CRUD + analytics
    launch     — Token launch flows (Doppler/Raydium)
"""
