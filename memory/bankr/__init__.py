"""
BANKR Bot integration module.

Provides:
  - BankrClient  — async HTTP client for api.bankr.bot Agent API
  - compose_*    — NL prompt composers (safe, structured → NL)
  - BankrSignals — signal publishing to bankrsignals.com
"""

from .client import BankrClient, BankrError, BankrDisabledError, compose_trade_prompt, compose_limit_prompt, compose_dca_prompt, compose_stop_loss_prompt, compose_launch_prompt  # noqa
from .signals import BankrSignals  # noqa

__all__ = [
    "BankrClient",
    "BankrError",
    "BankrDisabledError",
    "BankrSignals",
    "compose_trade_prompt",
    "compose_limit_prompt",
    "compose_dca_prompt",
    "compose_stop_loss_prompt",
    "compose_launch_prompt",
]
