from openai import AsyncOpenAI
from .config import settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def get_embedding(text: str) -> list[float]:
    client = _get_client()
    resp = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small",
    )
    return resp.data[0].embedding
