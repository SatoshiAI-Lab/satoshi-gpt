from ai.embedding import get_embeddings
from db.postgre import postgresql
from models import Reference

async def get_news_data(embedding, limit, similarity, filter_type: str = "embedding"):
    await postgresql.connect()
    rows = await postgresql.fetch_all(
        f"""
        SELECT title, content, published_at, similarity, url FROM (
            SELECT
                title,
                content,
                published_at,
                1 - ({filter_type} <=> :vec) AS similarity,
                url
            FROM news_filter
            where published_at > NOW() - INTERVAL '14 day'
            ORDER BY similarity DESC
        ) AS sub
        WHERE similarity > :similarity ORDER BY similarity DESC LIMIT :limit
        """,
        values={"vec": str(embedding[0]), "limit": limit, "similarity": similarity},
    )
    return rows


async def get_news_by_name(name: str, day: int = 7) -> list[Reference]:
    await postgresql.connect()

    rows = await postgresql.fetch_all(
        f"""
        SELECT title, content, created_at, source
        FROM news
        WHERE title LIKE '%{name}%' 
            AND created_at >= NOW() - INTERVAL ':day DAY'
        ORDER BY created_at DESC
        LIMIT 8
        """,
        values={"day": day},
    )

    ret: list[Reference] = []

    for r in rows:
        ret.append(
            Reference(
                title=r["title"],
                content=r["content"],
                type="news",
                published_at=r["created_at"],
                url=r["source"],
            )
        )

    return ret


async def get_news_pg(
    question: str, limit: int = 6, similarity: float = 0.7
) -> list[Reference]:
    embedding = await get_embeddings([question])
    rows = await get_news_data(embedding, limit, similarity, "title_embedding")
    ret: list[Reference] = []

    for row in rows:
        ret.append(
            Reference(
                title=row["title"],
                content=row["content"],
                type="news",
                published_at=row["published_at"],
                url=row["url"],
            )
        )
    return ret

