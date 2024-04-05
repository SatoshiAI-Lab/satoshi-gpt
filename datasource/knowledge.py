from ai.embedding import get_embeddings
from models import Knowledge
from db.postgre import postgresql


async def get_knowledge(
    question: str, limit: int = 5, similarity: float = 0.8
) -> list[Knowledge]:
    embedding = await get_embeddings([question])

    rows = await postgresql.fetch_all(
        """
        SELECT title, content, similarity FROM (
            SELECT
                title,
                content,
                1 - (title_vector <=> :vec) AS similarity 
            FROM knowledge
            ORDER BY similarity DESC
        ) AS sub
        WHERE similarity > 0.8 LIMIT 3
        """,
        values={"vec": str(embedding[0])},
    )

    ret: list[Knowledge] = []

    for row in rows:
        ret.append(
            Knowledge(
                title=row["title"],
                content=row["content"],
                similarity=row["similarity"],
            )
        )

    return ret
