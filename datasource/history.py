import json
from db.postgre import postgresql


async def get_history(uuid: str) -> list[dict]:
    # return []

    rows = await postgresql.fetch_all(
        query="select question, answer from history where uuid = :uuid order by id desc limit 3",
        values={"uuid": uuid},
    )
    rows.reverse()
    history: list[dict] = []
    for question, answer in rows:
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
    return history


async def get_history_nft(uuid: str, movie_type: str) -> list[dict]:
    rows = await postgresql.fetch_all(
        query="select question, answer from history where uuid = :uuid and model_name = :movie_type order by id desc limit 2",
        values={"uuid": uuid, "movie_type": movie_type},
    )
    rows.reverse()
    history: list[dict] = []
    for question, answer in rows:
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})

    return history


async def get_last_history_prompt_respchunk(uuid: str, movie_type: str):
    rows = await postgresql.fetch_all(
        query="select prompt,response_chunk from history where uuid = :uuid and model_name = :movie_type order by id desc limit 1",
        values={"uuid": uuid, "movie_type": movie_type},
    )
    prompt = rows[0][0]
    response_chunk = rows[0][1]
    return prompt, response_chunk


async def get_need_input_lines_vec(need_input_lines: str):
    rows = await postgresql.fetch_all(
        query="select lines_vec from zxc_need_input_lines where need_input_lines = :need_input_lines",
        values={"need_input_lines": need_input_lines},
    )
    return rows[0][0]


async def save_history(
    uuid: str,
    question: str,
    answer: str,
    prompt: list[dict],
    duration: float | None,
    response_chunk: list = [],
    is_error: int = 0,
    user_id: int | None = None,
    model_name: str = "chat",
    ip: str | None = None,
):
    await postgresql.execute(
        query="""
            insert into history (question, answer, uuid, prompt, duration, response_chunk,is_error,user_id,model_name,ip)
            values (:question, :answer, :uuid, :prompt, :duration, :response_chunk, :is_error, :user_id,:model_name,:ip)
        """,
        values={
            "question": question,
            "answer": answer,
            "uuid": uuid,
            "prompt": json.dumps(prompt, ensure_ascii=False, indent=4),
            "duration": duration,
            "response_chunk": json.dumps(response_chunk, ensure_ascii=False),
            "is_error": is_error,
            "user_id": user_id,
            "model_name": model_name,
            "ip": ip,
        },
    )


async def get_history_intent(uuid: str, intent_stream: str) -> tuple[list, str]:
    _intent_stream = intent_stream
    rows = await postgresql.fetch_all(
        query="select question, answer, is_intent from history where uuid = :uuid and is_error = 0 order by id desc limit 6",
        values={"uuid": uuid},
    )

    valid_index = 0
    for index, row in enumerate(rows):
        if row[2] == 0:
            valid_index = index
            break
    rows = rows[:valid_index]
    rows.reverse()

    history: list[dict] = []
    for question, answer, is_intent in rows:
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})

    return history, _intent_stream
