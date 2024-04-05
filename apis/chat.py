import json
import time
import traceback
import uuid
from ai.reference import references_controller
from datasource.history import save_history
from fastapi import Request, Response, Security
from fastapi.responses import JSONResponse, StreamingResponse
from apis import app
from logic.prepare import is_in_entities
from logic.user_question_event import question_event
from models.models import ChatUserQuery, Context, Entity, ResponseChunk 
from models.http_models import security


def response_chunk_format(string_data: str):
    json_string = string_data.replace("data: ", "")
    json_data = json.loads(json_string)
    result = {"data": json_data}

    return result



app.post("/chat",dependencies=[Security(security)])
async def chat(user_query: ChatUserQuery, request: Request, response: Response):
    begin = time.time()
    ctx = Context(question=user_query.question)
    if request.user:
        print("request.user", request.user)
        ctx.global_.user_id = request.user[0]

    ctx.global_.ip = 0
    ctx.global_.language = user_query.user_info.preference.language.lower()
    ctx.stream = user_query.stream

    ctx.global_.uuid = request.cookies.get("satoshi-gpt") or str(uuid.uuid4())

    # if from user choose entity
    if user_query.type and user_query.id:
        new_entity = Entity(id=user_query.id, name="", type=user_query.type)
        if not is_in_entities(ctx.selected_entities, new_entity):
            ctx.selected_entities.append(new_entity)

    for e in user_query.selected_entities:
        new_entity = Entity(id=e.id, name="", type=e.type)
        if is_in_entities(ctx.selected_entities, new_entity):
            continue
        ctx.selected_entities.append(new_entity)


    answer = question_event(ctx)

    async def gen():
        duration: float | None = None
        prompts: list[dict] = []
        texts: list[str] = []
        response_chunks: list[dict] = []
        is_error: int = 0

        try:
            is_interactive_response = False

            async for i in references_controller(answer):
                response_chunks.append(response_chunk_format(str(i)))

                if i.answer_type == "interactive":
                    is_interactive_response = True
                if i.text:
                    texts.append(i.text)
                    if duration is None and not "[debug]" in i.text:
                        duration = time.time() - begin
                if i.answer_type == "save_history":
                    prompts.extend(i.meta.get("prompt", []))
                    continue

                yield str(i)

            yield str(ResponseChunk(answer_type="end"))

        except Exception as e:
            is_error = 1
            error_message = traceback.format_exc()
            print(error_message)
            yield str(ResponseChunk(answer_type="chat_stream", text=error_message))
            texts.append(error_message)
            yield str(ResponseChunk(answer_type="end", error=error_message))

        finally:
            await save_history(
                ctx.global_.uuid,
                ctx.question,
                "".join(texts),
                prompts,
                duration=duration,
                response_chunk=response_chunks,
                is_error=is_error,
                user_id=ctx.global_.user_id,
                model_name="chat",
                ip=ctx.global_.ip,
            )

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Set-Cookie": f"satoshi-gpt={ctx.global_.uuid}; SameSite=None; Secure"
        },
    )
