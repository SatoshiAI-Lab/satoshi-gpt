from ai.reference import add_references, clear_references
from datasource.active_infos import get_active_infos_by_condition
from datasource.tools_risk_insight import get_future_unlock
from models import Context, Define_source, ResponseChunk
import datetime
from ai.GPT import gpt_gen_template_stream

from db.postgre import postgresql
from models import Reference
from .entities import token_release_destroy


async def get_token_change_mysql(
    token_id: int, colum_params: str = "percent_change_7_d"
):
    res = await postgresql.fetch_all(
        query=f"""
            select {colum_params} from token where id = :token_id;
        """,
        values={"token_id": token_id},
    )
    return res[0][0] or 0

def fluctuation_rule_filter(total_data_list: list[Reference]) -> list[Reference]:
    char_keys = ["airdrop"]
    res_list: list[Reference] = []
    for item in total_data_list:
        need_remove = False
        for char in char_keys:
            if char in item.content.lower():
                need_remove = True

        if not need_remove:
            res_list.append(item)

    return res_list

async def get_news_analysis_by_human_mysql(
    token_id: int, lang: str = "zh"
) -> list[Reference]:
    lang_dict = {"zh": "title", "zh": "title_en"}
    rows = await postgresql.fetch_all(
        query=f"""
            select {lang_dict[lang]}, token_id, n.updated_at
            from news n
            join news_link_token nlt on n.id = nlt.news_id
            where not {lang_dict[lang]} is null
                and token_id = :token_id
                and news_type_id in (15,16,17)
            order by updated_at desc
            limit 1;""",
        values={"token_id": token_id},
    )
    return [
        Reference(type="news", content=i[0], id=i[1], published_at=i[2]) for i in rows
    ]


async def get_news_analysis_by_human(id: int, lang: str = "zh") -> str:
    res = await get_news_analysis_by_human_mysql(id, lang)
    if not res:
        return ""

    res_news = ""
    updated_at_res = int(
        (datetime.datetime.now() - datetime.timedelta(days=7)).timestamp()
    )

    for item in res:
        string_time = str(item.published_at)
        updated_at = datetime.datetime.strptime(
            string_time, "%Y-%m-%d %H:%M:%S"
        ).timestamp()
        if int(updated_at) > updated_at_res:
            updated_at_res = int(updated_at)  
            res_news = item.content

    return res_news


async def check_btc_formula(token_id: int, time_type: str = "percent_change_7_d"):
    btc_change = await get_token_change_mysql(1, time_type)
    cur_token_change = await get_token_change_mysql(token_id, time_type)

    res_btc_formula = ""
    btc_is_rapid = False
    if cur_token_change > 0 and btc_change > 0:
        if cur_token_change - btc_change * 2 > 10:
            res_btc_formula = "up"
            if btc_change >= 5:
                btc_is_rapid = True
        else:
            if cur_token_change >= 10:
                res_btc_formula = "up"
            if btc_change >= 5:
                btc_is_rapid = True

    if cur_token_change < 0 and btc_change < 0:
        if -cur_token_change + -btc_change * 3 > 12:
            res_btc_formula = "down"
            if btc_change <= 5:
                btc_is_rapid = True
        else:
            if cur_token_change <= 10:
                res_btc_formula = "down"
            if btc_change <= 5:
                btc_is_rapid = True

    if cur_token_change >= 3 and btc_change < 0:
        if cur_token_change + -btc_change > 10:
            res_btc_formula = "up"
    if cur_token_change < 0 and btc_change > 0:
        if -cur_token_change + btc_change > 10:
            res_btc_formula = "down"

    return [res_btc_formula, btc_is_rapid]




async def get_formula_analysis_data(
    ctx: Context, token_id: int, formula_type: str
) -> list[Reference]:
    sentiment_type = 1 if formula_type == "up" else -1

    fluctuation_days = 14

    
    total_news_list = await get_active_infos_by_condition(
        ctx,
        entity_id=token_id,
        sentiments=[sentiment_type],
        pass_future="pass",
        day=fluctuation_days,
        include_sort=[Define_source(type="news")],
    )
    
    # total_news_list = rule_data_filter(total_news_list)
    total_news_list = fluctuation_rule_filter(total_news_list)

    ret = total_news_list

    
    if formula_type == "up":
        
        total_twitter_news = await get_active_infos_by_condition(
            ctx, entity_id=1, include_sort=[Define_source(type="twitter")]
        )
        
        # total_twitter_news = rule_data_filter(total_twitter_news)
        total_twitter_news = fluctuation_rule_filter(total_twitter_news)

        ret += total_twitter_news

    return ret



async def get_analysis_reason(
    references: list[Reference], formula_type: str, lang: str = "zh"
):
    template = (
        "news_analysis_up_v2" if formula_type == "up" else "news_analysis_down_v2"
    )
    reason_answer = await gpt_gen_template_stream(
        ctx=Context(question=""),
        answer_type="news_stream",
        template=template,
        lang=lang,
        references=references,
    )
    return reason_answer



async def get_after_formula_analysis(
    ctx, token_id: int, lang: str = "zh", itme_type: str = "percent_change_7_d"
):
    
    formula_type = ["", False]
    if token_id == 1:
        btc_7d = await get_token_change_mysql(1)
        if btc_7d >= 0:
            formula_type[0] = "up"
        else:
            formula_type[0] = "down"
    else:
        
        formula_type = await check_btc_formula(token_id, "percent_change_24_h")

        
        if formula_type[0] == "":
            formula_type = await check_btc_formula(token_id, itme_type)

    
    if formula_type[0]:
        ctx.fluctuation = formula_type[0]
        
        references = await get_formula_analysis_data(ctx, token_id, formula_type[0])

        
        have_fluctuation_content = False

        
        if references:
            
            add_ref = add_references(references)
            ctx.add_references = add_ref.meta
            yield add_ref
            
            async for i in await get_analysis_reason(references, formula_type[0], lang):
                ctx.live_content += i.text
                yield i
            
            yield clear_references()
            yield ResponseChunk(
                answer_type="news_stream", text="\n", hyper_text="", meta={}
            )
            have_fluctuation_content = True

        add_explain_no_gpt = {"up": "近期上涨是因为", "down": "近期下跌是因为"}

        
        if formula_type[1]:
            default_explain = {
                "up": "最近BTC的强烈反弹，调用了整体的市场情绪。\n",
                "down": "最近BTC下跌，导致市场情绪很恐慌。\n",
            }
            yield ResponseChunk(
                answer_type="news_stream",
                text=default_explain[formula_type[0]]
                if have_fluctuation_content
                else add_explain_no_gpt[formula_type[0]]
                + default_explain[formula_type[0]],
                hyper_text="",
                meta={},
            )
            have_fluctuation_content = True

        
        turnover_value = await get_token_change_mysql(token_id, "volume_24_h")
        if turnover_value < 50000:
            default_explain = {
                "up": "此币种交易深度不足，缺乏流动性，同时有新的资金开始埋伏，所以一买就涨，容易拉升。\n",
                "down": "此币种交易深度不足，缺乏流动性，有人一卖就可能会跌。\n",
            }
            yield ResponseChunk(
                answer_type="news_stream",
                text=default_explain[formula_type[0]]
                if have_fluctuation_content
                else add_explain_no_gpt[formula_type[0]]
                + default_explain[formula_type[0]],
                hyper_text="",
                meta={},
            )
            have_fluctuation_content = True

        
        if formula_type[0] == "down":

            twitter_data = await get_active_infos_by_condition(
                ctx,
                entity_id=token_id,
                pass_future="pass",
                day=7,
                include_sort=[Define_source(type="twitter")],
                is_origin=True,
            )

            if len(twitter_data) == 0:
                default_analysis = "项目方已经超过1周没有发布推特动态，不够活跃或有软跑路风险，让市场失去信心。\n"
                yield ResponseChunk(
                    answer_type="news_stream",
                    text=default_analysis
                    if have_fluctuation_content
                    else add_explain_no_gpt[formula_type[0]] + default_analysis,
                    hyper_text="",
                    meta={},
                )
                have_fluctuation_content = True


            release_price = await token_release_destroy(token_id)
            release_count = release_price["release_count"]

            release_value = release_count * release_price["token_price"]

            if release_value > 20000:
                
                
                yield ResponseChunk(
                    answer_type="news_stream",
                    text=f"目前每天有大约{release_count}个币释放，带来${release_value}抛压，抛压过大，所以下跌。\n",
                    hyper_text="",
                    meta={},
                )
                have_fluctuation_content = True

            
            new_release_add = await get_future_unlock(token_id, lang, "fluctuation")
            if new_release_add:
                yield ResponseChunk(
                    answer_type="news_stream",
                    text=new_release_add,
                    hyper_text="",
                    meta={},
                )

        
        else:
            token_7_percent = await get_token_change_mysql(token_id)
            if token_7_percent <= -15:
                default_analysis = "该币种最近价格过度下跌，低成本吸引了买入资金，因此超跌反弹。"
                yield ResponseChunk(
                    answer_type="news_stream",
                    text=default_analysis
                    if have_fluctuation_content
                    else add_explain_no_gpt[formula_type[0]] + default_analysis,
                    hyper_text="",
                    meta={},
                )
                have_fluctuation_content = True

            else:
                pass
                


        if have_fluctuation_content:
            yield ResponseChunk(
                answer_type="news_stream", text="\n\n", hyper_text="", meta={}
            )

        return

    return



async def get_news_analysis_main(ctx, id: int, lang: str = "zh"):
    
    res = await get_news_analysis_by_human(id, lang)
    if res:
        yield ResponseChunk(answer_type="news_stream", text=res, hyper_text="", meta={})
        yield ResponseChunk(
            answer_type="news_stream", text="\n\n", hyper_text="", meta={}
        )
        return

    
    async for i in get_after_formula_analysis(ctx, id, lang):
        yield i

    return

    
    
    
    

    
    

    
    

    
    
    

    
    
    
    
    

    
    
    
    
    
    
    
    
    
    
    
    
    
    

    
