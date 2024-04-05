from ai.reference import add_references, clear_references
from ai.GPT import gpt_gen_template_stream
from datasource.active_infos import get_active_infos_by_condition
from .entities import token_prompt_api, token_release_destroy
from datasource.twitter import get_twitter_by_token_links_mysql
import datetime
import time
from models import Context, Define_source, Entity 
from db.postgre import postgresql


async def get_token_market_rank(token_id: int):
    query = f"select rank_id from token where id = {token_id}"
    res = await postgresql.fetch_all(query)
    return res[0][0]


async def search_insight_mysql(token_id: int, lang: str):
    lang_dict = {"zh": "insight", "en": "insight_en"}
    return await postgresql.fetch_all(
        query=f"""
            select {lang_dict[lang]} from token_risk_insight where entity_id = :entity_id and not {lang_dict[lang]} is null
        """,
        values={"entity_id": token_id},
    )


async def insert_insight_mysql(token_id: int, lang: str, insight: str):
    lang_dict = {"zh": "insight", "en": "insight_en"}
    await postgresql.execute(
        query=f"""
        INSERT INTO token_risk_insight (entity_id, {lang_dict[lang]}) VALUES (:entity_id, :insight)
    """,
        values={"entity_id": token_id, "insight": insight},
    )
    return {"status": 200, "message": "ok", "entity_id": token_id}



async def get_softrun_tip(token_id: int, lang: str):
    origin_twitter_7days_data = await get_twitter_by_token_links_mysql(  
        token_id, 7, "origin"
    )
    lang_dict = {
        "zh": "项目方已超过1周未发布推特动态，当心有软跑路风险🏃\n\n",
        "en": "The project team has not released any Twitter updates for over a week. Beware of the risk of them potentially running away🏃\n\n",
    }

    if len(origin_twitter_7days_data) == 0:
        return lang_dict[lang]
    return None


def check_num(str):
    try:
        res_num = float(str)
        return res_num
    except:
        return str



async def get_inflastion_add(token_id: int, lang: str = "zh", symbol: str = ""):
    year_inflation_threshold = 10

    token_data = await token_prompt_api(token_id)
    year_inflation = token_data["token"]["inflation_rate"]

    release_price = await token_release_destroy(token_id)
    day_add_count = release_price["release_count"]
    day_add = day_add_count * release_price["token_price"]


    lang_dict = {
        "zh": {
            "inflation_rate": f"{symbol}年通胀率是{year_inflation}",
            "day_add": f"目前每天有{day_add_count}个币释放，带来的抛压有${day_add}\n",
        },
        "en": {
            "inflation_rate": f"The annual inflation rate of {symbol} is {year_inflation}",
            "day_add": f"Currently, there are {day_add_count} coins being released per day, bringing about selling pressure of ${day_add}\n",
        },
    }

    inflastion_add_res_list = []
    if year_inflation and year_inflation >= year_inflation_threshold:
        year_inflation_str = lang_dict[lang]["inflation_rate"]
        inflastion_add_res_list.append(year_inflation_str)
    else:
        inflastion_add_res_list.append(None)

    if check_num(day_add):
        day_add_str = lang_dict[lang]["day_add"]
        inflastion_add_res_list.append(day_add_str)
    else:
        inflastion_add_res_list.append(None)

    return inflastion_add_res_list



async def get_future_unlock(token_id: int, lang: str = "zh", func_type: str = "future"):
    query = (
        f"select unlock_time, is_cliff, value from token_lock where token_id={token_id}"
    )
    res = await postgresql.fetch_all(query=query)
    print("get_future_unlock", res)
    if len(res) > 0:
        value = round(res[0][2] / 10000, 2)
        lang_dict = {
            "zh": {
                "unlock_date": "{year}年{month}月{day}日",
                "unlock_line": "新增线性释放",
                "unlock_cliff": "新增悬崖式释放",
                "unlock_value": f"每天释放价值{value}万的代币 当心砸盘风险\n",
            },
            "en": {
                "unlock_date": "{year}/{month}/{day}",
                "unlock_line": "Add linear release",
                "unlock_cliff": "Add cliff release",
                "unlock_value": f"Be cautious of the risk of token dumping, which releases {value*10}k worth of value tokens every day\n",
            },
        }
        now_timestamp = time.time()
        if res[0][0] > now_timestamp:
            date = datetime.datetime.fromtimestamp(res[0][0])
            year = date.year
            month = date.month
            day = date.day

            formated_date = lang_dict[lang]["unlock_date"].format(
                year=year, month=month, day=day
            )
            print("formatedate", res[0][0], formated_date)

            unlock_style = (
                lang_dict[lang]["unlock_line"]
                if res[0][1] == 0
                else lang_dict[lang]["unlock_cliff"]
            )

            res_str_future = (
                f"{formated_date} {unlock_style} {lang_dict[lang]['unlock_value']}"
            )
            res_str_fluctuation = (
                f"{formated_date}有一轮新的释放，每天释放价值{value}万的代币，所以引发市场恐慌，导致下跌。"
            )
            res_return = (
                res_str_future if func_type == "future" else res_str_fluctuation
            )

            return res_return

    return ""


def remove_lightly_risk(text):
    key_word_list = ["爆仓", "跌破", "暴跌", "跌至", "跌幅", "跌了"]
    for key in key_word_list:
        if key in text:
            return True
    return False


def remove_lightly_risk_list(total_data_list: list):
    res_list = []
    for item in total_data_list:
        if not remove_lightly_risk(item[0]):
            res_list.append(item)

    return res_list



async def get_insight_summarize(ctx: Context, single_entity: Entity):
    before_market_rank = 2000
    before_twitter_days = 21

    token_rank = await get_token_market_rank(single_entity.id)

    if token_rank <= before_market_rank:
        
        references = await get_active_infos_by_condition(
            ctx,
            single_entity.id,
            sentiments=[-1],
            include_sort=[Define_source(type="news")],
        )

        # references = rule_data_filter(risk_data)
        
        if not references:
            return

        yield add_references(references)

        res_insight = ""
        async for i in await gpt_gen_template_stream(
            ctx=ctx,
            template="risk_insight_v2",
            answer_type="risk_analysis_stream",
            references=references,
            single_entity=single_entity,
        ):
            res_insight += i.text
            yield i

        yield clear_references()

        return

    return
