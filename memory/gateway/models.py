"""Normalized message protocol for all channels."""

from typing import Literal
from pydantic import BaseModel


class GatewayMessage(BaseModel):
    channel: Literal["whatsapp", "web", "telegram", "email"]
    sender_id: str
    sender_name: str | None = None
    content: str
    message_id: str | None = None
    metadata: dict = {}


class GatewayResponse(BaseModel):
    content: str
    channel: str
    recipient_id: str
    metadata: dict = {}
