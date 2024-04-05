import asyncio
from pydantic import BaseModel
import tqdm
import os
import json
import tiktoken
import dotenv

dotenv.load_dotenv()
import openai
import sqlite3
import hashlib
from utils import debug as print


def get_md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


embedding_cache = sqlite3.connect("embedding_cache.db")
embedding_cache_cur = embedding_cache.cursor()
embedding_cache_cur.execute(
    """
    CREATE TABLE IF NOT EXISTS embedding_cache (
        md5 TEXT PRIMARY KEY,
        text TEXT,
        embedding TEXT
    )
    """
)


def get_embedding_from_cache(md5: str) -> list[float] | None:
    if md5 == "d41d8cd98f00b204e9800998ecf8427e":
        return [0.0] * 1536  # empty string
    embedding_cache_cur.execute(
        "SELECT embedding FROM embedding_cache WHERE md5 = ?", (md5,)
    )
    res = embedding_cache_cur.fetchone()
    if res is None:
        return None
    return json.loads(res[0])


tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")


def get_token_length(text: str) -> int:
    return len(tokenizer.encode(text))


class Task(BaseModel):
    id: int
    text: str
    md5: str
    embedding: list[float] | None


async def get_embeddings(
    text: list[str], threads: int = 1, quiet: bool = False
) -> list[list[float]]:
    ids = list(range(len(text)))
    md5s = [get_md5(t) for t in text]
    embeddings = (get_embedding_from_cache(md5) for md5 in md5s)
    if len(text) > 100:
        embeddings = tqdm.tqdm(
            embeddings, desc="Querying embedding cache", total=len(text)
        )

    tasks: list[Task] = [
        Task(id=id, text=t, md5=md5, embedding=embedding)
        for id, t, md5, embedding in zip(ids, text, md5s, embeddings)
    ]

    query: list[Task] = [t for t in tasks if t.embedding is None]
    if not quiet:
        print(
            "OPENAI Embedding Query size",
            len(query),
            "tokens",
            sum(get_token_length(q.text) for q in query),
        )

    max_batch_token_length = 6939
    batch_token_length = 0
    batch_query: list[list[Task]] = []
    iter_batch: list[Task] = []
    for q in query:
        batch_token_length += get_token_length(q.text)
        if batch_token_length >= max_batch_token_length:
            batch_query.append(iter_batch)
            iter_batch = [q]
            batch_token_length = 0
        else:
            iter_batch.append(q)
    if iter_batch:
        batch_query.append(iter_batch)

    pbar = tqdm.tqdm(total=len(query), desc="OPENAI Embedding") if not quiet else None

    async def consumer() -> None:
        while batch_query:
            query = batch_query.pop()
            resp = await openai.Embedding.acreate(
                api_key=os.environ.get("EMBEDDING_API_KEY"),
                api_base=os.environ.get("EMBEDDING_API_BASE"),
                input=[q.text for q in query],
                model="text-embedding-ada-002",
            )
            assert isinstance(resp, dict)
            for q, i in zip(query, resp["data"]):
                embedding = i["embedding"]
                embedding_cache_cur.execute(
                    # ignore conflict
                    "INSERT OR IGNORE INTO embedding_cache (md5, text, embedding) VALUES (?, ?, ?)",
                    (q.md5, q.text, json.dumps(embedding)),
                )
                embedding_cache.commit()
                q.embedding = embedding
                if pbar:
                    pbar.update(1)

    if not quiet:
        print(f"Start {threads} consumer")
    await asyncio.gather(*[consumer() for _ in range(threads)])

    ret: list[Task] = sorted(tasks, key=lambda x: x.id)
    assert len(tasks) == len(ret)
    assert all([t.embedding is not None for t in ret])
    return [t.embedding for t in ret]  # type: ignore
