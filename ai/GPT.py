TIMEOUT = 39
import os
import datetime
import aiohttp
from fastapi import responses
import tiktoken
import asyncio
import hashlib
from pydantic import BaseModel
from datasource.active_infos import token_future_news, token_pass_news, token_risk_news
from db.mysql import mysql
from models import Context, ResponseChunk
from utils import debug as print
from dotenv import load_dotenv
import sqlite3
import re
import redis

from utils.check_data import check_is_pass_map

load_dotenv(verbose=True)
from utils.async_retry import tries
from utils.count_token import num_tokens_from_messages
from typing import AsyncGenerator, Self, Tuple, Union
import jinja2
import openai
import json
from utils.format import (
    format_price_cn,
    format_number_cn,
    format_change_percent,
    html2md,
    remove_lines,
)
from asyncache import cached
from cachetools import TTLCache


async def gpt_tools_no_stream(
    system: str, question: str, tools: list = [], history: list = []
):

    messages = [
        {
            "role": "system",
            "content": system,
        }
    ]

    for item in history:
        messages.append(item)

    messages.append({"role": "user", "content": question})

    res = await asyncio.wait_for(
        openai.ChatCompletion.acreate(
            
            model="gpt-4-1106-preview",
            temperature=0,
            messages=messages,
            tools=tools,
        ),
        timeout=TIMEOUT,
    )
    assert isinstance(res, dict)
    text = res["choices"][0]["message"]
    return text


pool = redis.ConnectionPool(host=os.getenv("REDIS_HOST"), port=6379, db=8)
redis_gpt_cache_cur = redis.Redis(connection_pool=pool)



def check_redis_gpt_cache(history_md5: str) -> str:
    if redis_gpt_cache_cur.exists(history_md5):
        result = redis_gpt_cache_cur.get(history_md5)
        return result.decode("utf-8") 
    else:
        return ""



def save_redis_gpt_cache(history_md5: str, answer: str):
    try:
        redis_gpt_cache_cur.set(history_md5, answer)
    except Exception as e:
        print("GPT缓存保存失败", e)


class SilentUndefined(jinja2.Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        print(f'jinja2.Undefined: "{self._undefined_name}" is undefined')
        return ""



def remove_empty_line(text: str) -> str:
    return "\n".join([i.strip() for i in text.split("\n") if i.strip()])


langdict = {
    "zh": "Chinese",
    "en": "English",
}


def render(template: str, **kargs) -> str:
    env = jinja2.Environment(undefined=SilentUndefined)
    env.filters["format_price_cn"] = format_price_cn
    env.filters["format_number_cn"] = format_number_cn
    env.filters["format_change_percent"] = format_change_percent
    env.filters["html2md"] = html2md
    env.filters["remove_lines"] = remove_lines
    env.filters["check_is_pass_map"] = check_is_pass_map
    env.filters["token_future_news"] = token_future_news
    env.filters["token_pass_news"] = token_pass_news
    env.filters["token_risk_news"] = token_risk_news
    temp = env.from_string(template)

    def now() -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d")

    temp.globals["now"] = now
    
    return remove_empty_line(temp.render(langdict=langdict, **kargs))


class Template(BaseModel):
    system: str
    examples: list[str]
    query: str
    model: str
    temperature: float
    functions: list[dict]
    fixed_format: bool
    frequency_penalty: float
    examples_in_system: bool
    json_mode: bool

    def render(self, **kargs) -> Self:
        self.system = render(self.system, **kargs)
        self.examples = [render(i, **kargs) for i in self.examples]
        self.query = render(self.query, **kargs)

        return self

    def generate_messages(self, history: list[dict], quiet: bool = False) -> list[dict]:
        
        messages = [{"role": "system", "content": self.system}] if self.system else []
        for index, exp in enumerate(self.examples):
            if self.examples_in_system:
                messages.append(
                    {
                        "role": "system",
                        "name": "example_user"
                        if index % 2 == 0
                        else "example_assistant",
                        "content": exp,
                    }
                )
            else:
                messages.append(
                    {
                        "role": "user" if index % 2 == 0 else "assistant",
                        "content": exp,
                    }
                )
        messages.extend(history)
        messages.append({"role": "user", "content": self.query})

        
        if self.model.endswith("auto"):
            tokens = len(
                tiktoken.encoding_for_model("gpt-3.5-turbo").encode(
                    "\n".join([i["content"] for i in messages])
                )
            )
            if not quiet:
                print("tokens", tokens)
            self.model = (
                "gpt-3.5-turbo-0613" if tokens < 3500 else "gpt-3.5-turbo-16k-0613"
            )

        return messages


async def get_template(template: str) -> Template:
    ret = await _get_template(template)

    
    ret = ret.model_copy()

    return ret


@cached(TTLCache(8192, 1))
async def _get_template(template: str) -> Template:
    rows = await mysql.fetch_all(
        query="""
            select
                system,
                examples,
                query,
                model,
                temperature,
                functions,
                fixed_format,
                frequency_penalty,
                examples_in_system,
                json_mode
            from prompt_templates
            where name = :template
            limit 1
            """,
        values={"template": template},
    )
    if not rows:
        raise Exception(f"模板 {template} 不存在")
    (
        system,
        examples,
        query,
        model,
        temperature,
        functions,
        fixed_format,
        frequency_penalty,
        examples_in_system,
        json_mode,
    ) = rows[0]
    functions = functions or []

    ret = Template(
        system=system,
        examples=examples,
        query=query,
        model=model,
        temperature=temperature,
        functions=functions,
        fixed_format=fixed_format,
        frequency_penalty=frequency_penalty,
        examples_in_system=examples_in_system,
        json_mode=json_mode,
    )

    return ret


async def gpt_gen_template(
    ctx: Context,
    template: str,
    stream=False,
    answer_type: str = "chat_stream",
    quiet: bool = False,
    **kargs,
) -> Tuple[list[dict], str] | Tuple[list[dict], dict] | Tuple[
    list[dict], AsyncGenerator[ResponseChunk, None]
]:
    template_obj = await get_template(template)

    
    template_obj.render(ctx=ctx, **kargs)

    
    messages = template_obj.generate_messages(ctx.history, quiet=quiet)

    
    if quiet:
        if os.environ.get("SATOSHI_DEVELOPMENT"):
            print(
                template,
                "messages",
                json.dumps(messages, ensure_ascii=False, indent=2).replace("\\n", "\n"),
            )
        else:
            print(template, "messages", messages)

    
    if template_obj.fixed_format:
        if not stream:
            return messages, template_obj.query

        
        async def gen():
            batch_size = 3
            
            yield ResponseChunk(
                answer_type="save_history",
                meta={
                    "prompt": messages,
                    "query": ctx.question,
                    "answer": template_obj.query,
                },
            )
            for t in range(0, len(template_obj.query), batch_size):
                text = template_obj.query[t : t + batch_size]
                yield ResponseChunk(answer_type=answer_type, text=text)
                await asyncio.sleep(0.01)

        return messages, gen()

    
    history_md5 = hashlib.md5(
        (
            template_obj.model
            + "|"
            + str(template_obj.temperature)
            + "|"
            + str(template_obj.frequency_penalty)
            + "|"
            + str(template_obj.json_mode)
            + "|"
            + json.dumps(messages + template_obj.functions, ensure_ascii=False)
        ).encode("utf-8")
    ).hexdigest()
    if gpt_cache_str := check_redis_gpt_cache(history_md5):
        if template_obj.functions:
            assert not stream
            function_call = json.loads(gpt_cache_str)
            return messages, function_call

        if not stream:
            return messages, gpt_cache_str

        
        async def gen():
            batch_size = 3
            
            yield ResponseChunk(
                answer_type="save_history",
                meta={
                    "prompt": messages,
                    "query": ctx.question,
                    "answer": gpt_cache_str,
                },
            )
            if os.environ.get("SATOSHI_DEVELOPMENT"):
                yield ResponseChunk(answer_type=answer_type, text=gpt_cache_str)
                return
            
            for t in range(0, len(gpt_cache_str), batch_size):
                text = gpt_cache_str[t : t + batch_size]
                yield ResponseChunk(answer_type=answer_type, text=text)
                await asyncio.sleep(0.01)

        return messages, gen()

    if template_obj.functions:
        assert not stream

        
        res = await asyncio.wait_for(
            openai.ChatCompletion.acreate(
                model=template_obj.model,
                temperature=template_obj.temperature,
                messages=messages,
                stream=False,
                functions=template_obj.functions,
                function_call="auto",
            ),
            timeout=None,
        )
        assert isinstance(res, dict)
        message = res["choices"][0]["message"]
        function_call = message.get("function_call", {})
        save_redis_gpt_cache(history_md5, json.dumps(function_call))
        return messages, function_call
    
    res = await asyncio.wait_for(
        openai.ChatCompletion.acreate(
            model=template_obj.model,
            temperature=template_obj.temperature,
            messages=messages,
            stream=stream,
            frequency_penalty=template_obj.frequency_penalty,
            response_format={"type": "json_object"} if template_obj.json_mode else None,
        ),
        timeout=TIMEOUT if stream else None,
    )
    if not stream:
        assert isinstance(res, dict)
        text = res["choices"][0]["message"]["content"]
        save_redis_gpt_cache(history_md5, text)
        return messages, text

    
    async def gen():
        assert isinstance(res, AsyncGenerator)
        texts: list[str] = []
        
        yield ResponseChunk(
            answer_type="save_history",
            meta={
                "prompt": messages,
                "query": ctx.question,
                "answer": "".join(texts),
            },
        )
        async for i in res:
            assert isinstance(i, dict)
            content = i["choices"][0]["delta"].get("content")
            if content is None:
                break

            yield ResponseChunk(answer_type=answer_type, text=content)
            texts.append(content)

        
        save_redis_gpt_cache(history_md5, "".join(texts))

        yield ResponseChunk(answer_type=answer_type, text="", finish_reason="done")

        return

    return messages, gen()


class GPTFunctionCallResult(BaseModel):
    name: str
    arguments: dict

    def __bool__(self) -> bool:
        return all([self.name, self.arguments])


async def gpt_gen_template_function(
    ctx: Context, template: str, *args, **kwargs
) -> GPTFunctionCallResult:
   
    _, result = await gpt_gen_template(ctx, template, *args, **kwargs)
    assert isinstance(result, dict)

    
    name = result.get("name", "")
    arguments = json.loads(result.get("arguments", "{}"))

    ret = GPTFunctionCallResult(name=name, arguments=arguments)

    return ret


async def gpt_gen_template_stream(
    ctx: Context | None = None,
    template: str = "default",
    answer_type: str | None = None,
    *args,
    **kwargs,
) -> AsyncGenerator[ResponseChunk, None]:
    if ctx is None:
        ctx = Context(question="")
    if answer_type is None:
        answer_type = "chat_stream"
    _, result = await gpt_gen_template(
        ctx, template, True, answer_type, *args, **kwargs
    )
    assert isinstance(result, AsyncGenerator)
    return result


async def gpt_gen_template_text(
    ctx: Context | None = None, template: str = "default", *args, **kwargs
) -> str:
    if ctx is None:
        ctx = Context(question="")
    ret: str = ""
    async for i in await gpt_gen_template_stream(ctx, template, *args, **kwargs):
        assert isinstance(i, ResponseChunk)
        ret += i.text
    assert isinstance(ret, str)
    
    return ret
