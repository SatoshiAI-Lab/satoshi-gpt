import datetime
from models import Reference, ResponseChunk
from typing import Any, AsyncGenerator
import copy


def add_references(refs: list[Reference]):
    new_refs = copy.deepcopy(refs)
    for i in new_refs:
        if isinstance(i.datetime_str, datetime.datetime):
            i.datetime_str = i.datetime_str.strftime("%Y-%m-%d %H:%M:%S")

    references = {str(num): i.model_dump() for num, i in enumerate(new_refs, 1)}
    return ResponseChunk(answer_type="references_add", meta=references)


def clear_references():
    return ResponseChunk(answer_type="references_clear")


def is_num(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


async def references_controller(
    answer: AsyncGenerator[ResponseChunk, Any]
) -> AsyncGenerator[ResponseChunk, Any]:
    references: dict[str, Reference] = {}

    references_text: str = ""

    async for i in answer:
        if i.answer_type == "references_add":
            references.update(i.meta)
            continue

        if i.answer_type == "references_clear":
            references.clear()
            continue

        if "[" not in i.text and "]" not in i.text and not is_num(i.text):
            yield i
            continue

        if not references:
            yield i
            continue

        if not i.text:
            yield i
            continue

        for index, t in enumerate(i.text):
            if t == "[":
                if references_text:
                    yield ResponseChunk(
                        answer_type=i.answer_type,
                        text=references_text,
                        meta=i.meta,
                    )
                references_text = "["
                continue

            if references_text:
                if t == "]":
                    references_num = references_text.strip("[]")
                    if not references_num in references:
                        yield ResponseChunk(
                            answer_type=i.answer_type,
                            text=f"(wrong references: {references_num})",
                            meta=i.meta,
                        )
                        references_text = ""
                        continue
                    yield ResponseChunk(
                        answer_type="reference",
                        text=f"[{references_num}]",
                        meta=references[references_num],
                    )
                    references_text = ""
                    continue
                if t.isnumeric():
                    references_text += t
                    continue

                yield ResponseChunk(
                    answer_type=i.answer_type,
                    text=references_text,
                    meta=i.meta,
                )
                references_text = ""

            yield ResponseChunk(
                answer_type=i.answer_type,
                text=t,
                meta=i.meta,
            )

    return
