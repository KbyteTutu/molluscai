"""
Pluggable embedding + rerank provider adapters.

Each provider implements the OpenAI-compatible /v1/embeddings or /v2/embed shape
plus the SiliconFlow/Cohere/Jina-compatible /rerank shape. Callers use
`get_embedding_provider(cfg)` / `get_rerank_provider(cfg)` — they pick the right
adapter by `cfg.provider`.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Iterable, Protocol

import httpx

log = logging.getLogger(__name__)


@dataclass(slots=True)
class EmbedResult:
    vectors: list[list[float]]
    input_tokens: int
    total_tokens: int
    latency_ms: int
    model_id: str


@dataclass(slots=True)
class RerankHit:
    index: int
    score: float


@dataclass(slots=True)
class RerankResult:
    hits: list[RerankHit]
    input_tokens: int
    total_tokens: int
    latency_ms: int
    model_id: str


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> EmbedResult: ...


class RerankProvider(Protocol):
    async def rerank(self, query: str, documents: list[str], top_n: int) -> RerankResult: ...


class _BaseClient:
    def __init__(self, base_url: str, api_key: str, model_id: str, *, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_id = model_id
        self.timeout = timeout

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    @staticmethod
    def _ms(start_ns: int, end_ns: int) -> int:
        return int((end_ns - start_ns) / 1_000_000)


class OpenAICompatEmbedding(_BaseClient):
    """
    Works with SiliconFlow, Jina, OpenAI, Voyage, and any OpenAI-schema provider.
    Request:  POST {base}/embeddings  body={model, input, encoding_format?}
    Response: {data: [{embedding, index}], usage: {prompt_tokens, total_tokens}}
    """

    async def embed(self, texts: list[str]) -> EmbedResult:
        import time
        start = time.perf_counter_ns()
        async with self._client() as client:
            r = await client.post(
                "/embeddings",
                json={
                    "model": self.model_id,
                    "input": texts,
                    "encoding_format": "float",
                },
            )
            r.raise_for_status()
            data = r.json()
        end = time.perf_counter_ns()
        items = sorted(data["data"], key=lambda x: x["index"])
        usage = data.get("usage") or {}
        return EmbedResult(
            vectors=[it["embedding"] for it in items],
            input_tokens=int(usage.get("prompt_tokens") or usage.get("total_tokens") or 0),
            total_tokens=int(usage.get("total_tokens") or usage.get("prompt_tokens") or 0),
            latency_ms=self._ms(start, end),
            model_id=data.get("model", self.model_id),
        )


class SiliconFlowRerank(_BaseClient):
    """
    SiliconFlow rerank — also followed by Jina. Both accept the same shape.
    Request:  POST {base}/rerank  body={model, query, documents[], top_n, return_documents:false}
    Response: {results: [{index, relevance_score}], tokens: {input_tokens, output_tokens}}
    """

    async def rerank(self, query: str, documents: list[str], top_n: int) -> RerankResult:
        import time
        start = time.perf_counter_ns()
        async with self._client() as client:
            r = await client.post(
                "/rerank",
                json={
                    "model": self.model_id,
                    "query": query,
                    "documents": documents,
                    "top_n": top_n,
                    "return_documents": False,
                },
            )
            r.raise_for_status()
            data = r.json()
        end = time.perf_counter_ns()
        results = data.get("results", [])
        tokens = data.get("tokens") or data.get("usage") or {}
        return RerankResult(
            hits=[RerankHit(index=int(h["index"]), score=float(h["relevance_score"])) for h in results],
            input_tokens=int(tokens.get("input_tokens") or tokens.get("prompt_tokens") or 0),
            total_tokens=int(tokens.get("total_tokens")
                              or (tokens.get("input_tokens", 0) + tokens.get("output_tokens", 0))),
            latency_ms=self._ms(start, end),
            model_id=data.get("model", self.model_id),
        )


def get_embedding_provider(provider: str, base_url: str, api_key: str, model_id: str) -> EmbeddingProvider:
    p = provider.lower()
    if p in {"siliconflow", "jina", "openai", "voyage", "openai-compat", "openai_compat"}:
        default_base = {
            "siliconflow": "https://api.siliconflow.cn/v1",
            "jina": "https://api.jina.ai/v1",
            "openai": "https://api.openai.com/v1",
            "voyage": "https://api.voyageai.com/v1",
        }.get(p)
        return OpenAICompatEmbedding(base_url or default_base or base_url, api_key, model_id)
    raise ValueError(f"unknown embedding provider: {provider!r}")


def get_rerank_provider(provider: str, base_url: str, api_key: str, model_id: str) -> RerankProvider:
    p = provider.lower()
    if p in {"siliconflow", "jina", "openai-compat", "openai_compat"}:
        default_base = {
            "siliconflow": "https://api.siliconflow.cn/v1",
            "jina": "https://api.jina.ai/v1",
        }.get(p)
        return SiliconFlowRerank(base_url or default_base or base_url, api_key, model_id)
    raise ValueError(f"unknown rerank provider: {provider!r}")


def compose_taxon_text(row: dict) -> str:
    """Composite description used both to embed the taxon and to hash for cache keying."""
    parts: list[str] = [row["scientificname"]]
    if row.get("authority"):
        parts.append(row["authority"])
    if row.get("rank"):
        parts.append(f"({row['rank']})")
    chain = [row.get(k) for k in ("kingdom", "phylum", "class", "order", "family", "genus")]
    chain = [x for x in chain if x]
    if chain:
        parts.append("Classification: " + " > ".join(chain))
    if row.get("species_epithet"):
        parts.append(f"Species epithet: {row['species_epithet']}")
    habitat = []
    for key, label in [
        ("is_marine", "marine"), ("is_brackish", "brackish"),
        ("is_freshwater", "freshwater"), ("is_terrestrial", "terrestrial"),
    ]:
        if row.get(key):
            habitat.append(label)
    if habitat:
        parts.append("Habitat: " + ", ".join(habitat))
    if row.get("is_extinct"):
        parts.append("Extinct taxon.")
    return " — ".join(parts)


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def pad_or_truncate(vec: list[float], target_dim: int = 2000) -> list[float]:
    n = len(vec)
    if n == target_dim:
        return vec
    if n > target_dim:
        return vec[:target_dim]
    return vec + [0.0] * (target_dim - n)
