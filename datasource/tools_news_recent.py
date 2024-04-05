import asyncio
from ai.GPT import gpt_gen_template_stream
from ai.reference import add_references, clear_references
from datasource.active_infos import get_active_infos, get_active_infos_by_condition
from datasource.tools_risk_insight import get_token_market_rank
from utils import debug as print
from models import Context, Define_source, Entity, ResponseChunk
from typing import AsyncGenerator

async def get_recent_situation(
    ctx: Context, token: Entity, is_ask_what: bool = False
) -> AsyncGenerator[ResponseChunk, None]:
    recent_lastest_tip = 7
    recent_longest_tip = 22

    recent_day = 15  
    recent_day_sub = 22  

    lang_dict = {
        "zh": {
            "day_lastest_no_news": f"项目方已经{recent_lastest_tip}天没有发布推特了🤔\n",
            "day_longest_no_news": f"项目方已经{recent_longest_tip}天没有发布推特了🤔\n\n",
        },
        "en": {
            "day_lastest_no_news": f"The project team has not tweeted for {recent_lastest_tip} days🤔\n",
            "day_longest_no_news": f"The project team has not tweeted for {recent_longest_tip} days🤔\n\n",
        },
    }
    
    (
        day_lastest_news_origin,
        day_lastest_news_sub,
        day_lastest_news,
        
    ) = await asyncio.gather(
        
        
        get_active_infos(
            entity_id=token.id,
            day=recent_lastest_tip,
            is_origin=True,
            only_twitter=True,
        ),
        get_active_infos(
            entity_id=token.id, day=recent_day_sub, is_origin=True, only_twitter=True
        ),
        
        
        get_active_infos_by_condition(
            ctx,
            entity_id=token.id,
            pass_future="pass",
            day=recent_day,
            include_sort=[Define_source(type="news"), Define_source(type="twitter")],
        ),
        
        
    )

    
    token_rank = await get_token_market_rank(token.id)
    if token_rank and token_rank <= 2000:
        
        if len(day_lastest_news_origin) == 0 and len(day_lastest_news_sub) > 0:
            yield ResponseChunk(
                answer_type="news_stream",
                text=lang_dict[ctx.global_.language]["day_lastest_no_news"],
                hyper_text="",
                meta={},
            )
        if len(day_lastest_news_sub) == 0:
            yield ResponseChunk(
                answer_type="news_stream",
                text=lang_dict[ctx.global_.language]["day_longest_no_news"],
                hyper_text="",
                meta={},
            )
    if not total_data_list:
        day_lastest_news_sub = await get_active_infos_by_condition(
            ctx,
            entity_id=token.id,
            pass_future="pass",
            day=recent_day_sub,
            include_sort=[Define_source(type="news"), Define_source(type="twitter")],
        )
        
        if not day_lastest_news_sub:
            if not is_ask_what:
                yield ResponseChunk(answer_type="news_stream", text="近期没有相关动态\n")
            return

        
        total_data_list = day_lastest_news_sub

    
    yield add_references(total_data_list)

    
    gpt_answer = ""
    async for i in await gpt_gen_template_stream(
        ctx=ctx,
        template="recent_situation_v2",
        answer_type="news_stream",
        total_data_list=total_data_list,
        single_entity=token,
    ):
        gpt_answer += i.text
        yield i

    
    yield clear_references()

    yield ResponseChunk(answer_type="news_stream", text="\n\n")
