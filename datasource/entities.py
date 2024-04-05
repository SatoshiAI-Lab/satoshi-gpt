import datetime
from typing import Any, Coroutine, Literal
import aiohttp
import asyncio
from datasource.active_infos import (
    get_active_infos_by_embedding,
    get_active_infos_by_time,
)

from models.models import Entity, ENTITYTYPE2ID, No_entity, NOENTITYTYPE2ID 
from db.postgre import postgresql
import time

from utils.format import timestamp_to_datetime_str

async def get2(url: str, params: dict) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            j = await resp.json()
            return j


async def get(url: str, params: dict) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if not resp.status == 200:
                return {}
            j = await resp.json()
            if j.get("status") != 200:
                return {}
            return j["data"]


async def post(url: str, params: dict) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params) as resp:
            if not resp.status == 200:
                return {}
            j = await resp.json()
            if j.post("status") != 200:
                return {}
            return j["data"]


async def token_release_destroy(token_id: int) -> dict[str, float]:
    release_count, token_price = await asyncio.gather(
        postgresql.fetch_all(
            """
            SELECT (
                (SELECT circulating_supply FROM token_ts_data WHERE freq = '1d' AND token_id = :id ORDER BY collected_at DESC LIMIT 1)
                -
                (SELECT circulating_supply FROM token_ts_data WHERE freq = '1d' AND token_id = :id ORDER BY collected_at DESC LIMIT 1 OFFSET 1)
            ) AS circulating_supply_difference;
            """,
            values={"id": token_id},
        ),
        postgresql.fetch_all(
            """
            SELECT price from token where id = :id;
            """,
            values={"id": token_id},
        ),
    )
    ret: dict[str, float] = {"release_count": 0, "token_price": 0}
    if release_count[0][0]:
        ret["release_count"] = release_count[0][0]
    if token_price[0][0]:
        ret["token_price"] = token_price[0][0]

    return ret


async def token_prompt_api(id: int) -> dict:
    
    (
        basic,
        token_label_rank_market,
        token_label_rank_tvl,
    ) = await asyncio.gather(
        postgresql.fetch_one("select * from token where id = :id", values={"id": id}),
        
        postgresql.fetch_all(
            """
            SELECT name, count(label_id) as rank_, label_id FROM (
                SELECT t.id, t.market_cap, tll.label_id, l.name
                FROM token t
                JOIN token_link_label tll ON t.id = tll.token_id
                JOIN label l ON l.id = tll.label_id 
                WHERE tll.label_id IN (
                    SELECT label_id
                    FROM token_link_label
                    WHERE token_id = :id
                ) AND t.market_cap >= (
                    FROM token
                    WHERE id = :id
                ) and l.is_deleted = 0 and tll.is_deleted = 0
            ) sub
            GROUP BY label_id, name
            """,
            values={"id": id},
        ),
        postgresql.fetch_all(
            """
            SELECT name, count(label_id) AS rank_
                SELECT t.id, t.tvl, tll.label_id, l.name
                FROM token t
                JOIN token_link_label tll ON t.id = tll.token_id
                    SELECT label_id
                    FROM token_link_label
                    WHERE token_id = :id
                    SELECT tvl
                    FROM token
                    WHERE id = :id
                )
                ORDER BY tll.label_id, t.tvl DESC
            ) sub
            ORDER BY rank_ DESC, name;
            """,
            values={"id": id},
        )
    )

    (token_label_rank_turnover, chain, route_map) = await asyncio.gather(
        
        postgresql.fetch_all(
            """
            SELECT name, count(label_id) as rank_
            FROM (
                FROM token t
                JOIN token_link_label tll ON t.id = tll.token_id
                JOIN label l ON l.id = tll.label_id 
                    SELECT label_id
                    FROM token_link_label
                    WHERE token_id = :id
                ) AND t.turnover >= (
                    SELECT turnover
                    FROM token
                    WHERE id = :id
                )
            ) sub
            GROUP BY name
            """,
            values={"id": id},
        ),
        postgresql.fetch_all(
            """
            select tcd.address, c.symbol from token_chain_data tcd 
            join chain c on c.platform_id = tcd.platform_id
            where tcd.token_id = :id
            """,
            values={"id": id},
        ),
        postgresql.fetch_all(
            """
            select rm.published_time, rm.title from route_map rm
            where tlrm.token_id = :id
            order by rm.estimated_time desc
            limit 5;
            """,
            values={"id": id},
        ),
    )
    (
        unlock,
        exchanges,
    ) = await asyncio.gather(
        
        postgresql.fetch_all(
            """
            select unlock_time, amount, value, is_cliff from token_lock where token_id = :id
            """,
            values={"id": id},
        ),
        postgresql.fetch_all(
            """SELECT cmc_exchange_name, sum(volume) AS volume_sum
            FROM token_pair tp
            WHERE tp.token_id = :id
            GROUP BY cmc_exchange_name
            ORDER BY volume_sum DESC;
            """,
            values={"id": id},
        )
    )

    ret = dict(basic or {})
    ret["early_cost"] = [i for i in ret["early_cost"] or "[]"]
    market_rank = [
        {"name": i[0], "rank": i[1], "label_id": i[2]}
        for i in token_label_rank_market or []
    ]
    tvl_rank = [{"name": i[0], "rank": i[1]} for i in token_label_rank_tvl or []]
    turnover_rank = [
        {"name": i[0], "rank": i[1]} for i in token_label_rank_turnover or []
    ]
    ret["labels_info"] = {
        "market_rank": market_rank,
        "tvl_rank": tvl_rank,
        "turnover_rank": turnover_rank,
    }
    if unlock:
        unlock = [i for i in unlock[0]]
        unlock[0] = timestamp_to_datetime_str(unlock[0])

    half_time = ret.get("half_time", 0)
    if half_time:
        now_timestamp = time.time()
        datetime_str = timestamp_to_datetime_str(half_time)
        if half_time > now_timestamp:
            ret["half_time"] = "下一次减半时间是" + datetime_str
        else:
            ret["half_time"] = "上一次减半时间是" + datetime_str

    
    unlocks_issuance = ret.get("unlocks_issuance", 0)
    issuance_everyday = ret.get("issuance_everyday", 0)
    price = ret.get("price", 0)
    add_supply = 0
    add_value = 0

    if unlocks_issuance != None:
        add_supply = unlocks_issuance
        add_value = unlocks_issuance * price
    elif price and issuance_everyday:
        add_supply = round(issuance_everyday / price, 2)
        add_value = issuance_everyday

    ret["add_supply"] = add_supply
    ret["add_value"] = add_value
    ret["chain"] = chain
    ret["unlock"] = unlock
    ret["route_map"] = []
    for item in route_map or []:
        title_obj = item[1]
        title_str = (
            title_obj.get("zh") or title_obj.get("en") or list(title_obj.values())[0]
        )

        ret["route_map"].append({"publish_time": item[0], "title": title_str})

    

    ret["exchanges"] = exchanges

    return {"token": ret}


async def label_prompt_api(id: int) -> dict:
    label_data = await postgresql.fetch_all(
        query="""select symbol, price, market_cap, percent_change_24_h,tvl,volume_24_h from token t
join token_link_label tll on tll.token_id = t.id 
join label l on l.id = tll.label_id 
where l.id = :id and tll.is_deleted = 0 order by market_cap desc""",
        values={"id": id},
    )
    label_token_sum = await postgresql.fetch_all(
        query="""select count(*) from token_link_label where label_id = :id""",
        values={"id": id},
    )
    return {"label": label_data, "token_sum": label_token_sum[0][0]}


async def no_entity_token(question: str) -> dict:
    fluc_type = "desc"
    if "跌" in question:
        fluc_type = "asc"
        if "涨" in question:
            fluc_type = "desc"

    market_rank, fluc_24h_rank, fluc_7d_rank, fluc_30d_rank = await asyncio.gather(
        postgresql.fetch_all(
            query="""select symbol,price,market_cap from token order by rank_id asc limit 10"""
        ),
        postgresql.fetch_all(
            query=f"""select symbol,price,percent_change_24_h from token where rank_id <= 500 order by percent_change_24_h {fluc_type} limit 10"""
        ),
        postgresql.fetch_all(
            query=f"""select symbol,price,percent_change_7_d from token where rank_id <= 500 order by percent_change_7_d {fluc_type} limit 10"""
        ),
        postgresql.fetch_all(
            query=f"""select symbol,price,percent_change_30_d from token where rank_id <= 500 order by percent_change_30_d {fluc_type} limit 10"""
        ),
    )

    ret = dict(
        fluc_type="上涨" if fluc_type == "desc" else "下跌",
        market_rank=market_rank,
        fluc_24h_rank=fluc_24h_rank,
        fluc_7d_rank=fluc_7d_rank,
        fluc_30d_rank=fluc_30d_rank,
    )
    return {"no_entity_token": ret}


async def no_entity_label(question: str) -> dict:
    fluc_type = "desc"
    time_filter = "percent_change_24_h"
    if "跌" in question:
        fluc_type = "asc"
        if "涨" in question:
            fluc_type = "desc"
    if "7天" in question:
        time_filter = "percent_change_7_d"

    market_fluc_rank, token_sum_rank, updown_num_rank = await asyncio.gather(
        
        postgresql.fetch_all(
            f""" select l.name, sum(change_value) / sum(sub.market_cap) as change_percent from label l 
            join token_link_label tll on l.id = tll.label_id 
            join (select id, name, market_cap,  market_cap * {time_filter} as change_value from token where rank_id < 9999 order by change_value desc) as sub on sub.id = tll.token_id 
            where tll.is_deleted = 0 and l.is_deleted = 0
            group by l.id
            order by change_percent desc limit 15
        """
        ),
        
        postgresql.fetch_all(
            """SELECT l.name, COUNT(DISTINCT tll.token_id) as num_tokens FROM token_link_label tll
             join label l on l.id = tll.label_id where tll.is_deleted = 0 and l.is_deleted = 0
            GROUP BY l.name order by num_tokens desc limit 15"""
        ),
        
        postgresql.fetch_all(
            f"""select l.name, count(DISTINCT sub.id) as up_num from label l 
            join token_link_label tll on l.id = tll.label_id 
            join (
                select id from token where rank_id < 9999 and {time_filter} > 0.001
            ) as sub on sub.id = tll.token_id 
            where tll.is_deleted = 0 and l.is_deleted = 0
            group by l.id order by up_num {fluc_type} limit 15"""
        ),
        
    )

    ret = dict(
        fluc_type="上涨" if fluc_type == "desc" else "下跌",
        market_fluc_rank=market_fluc_rank,
        token_sum_rank=token_sum_rank,
        updown_num_rank=updown_num_rank,
    )

    return {"no_entity_label": ret}


async def no_entity_software(question: str) -> dict:
    await postgresql.connect()
    # langu
    type_key = {
        "交易": "swap",
        "钱包": "wallet",
        "线": "inquiry",
        "币": "inquiry",
        "聊天": "sociality",
        "社交": "sociality",
        "平台": "sociality",
        "工具": "other",
    }
    type_name = "swap"
    for key, val in type_key.items():
        if key in question:
            type_name = val

    swap = await postgresql.fetch_all(
        """select name, android_url from software where category = 'swap' order by downloads desc limit 5"""
    )
    wallet = await postgresql.fetch_all(
        """select name, android_url from software where category = 'wallet' order by downloads desc limit 5"""
    )
    inquiry = await postgresql.fetch_all(
        """select name, android_url from software where category = 'inquiry' order by downloads desc limit 5"""
    )
    sociality = await postgresql.fetch_all(
        """select name, android_url from software where category = 'sociality' order by downloads desc limit 5"""
    )
    other = await postgresql.fetch_all(
        """select name, android_url from software where category = 'other' order by downloads desc limit 5"""
    )
    rank = await postgresql.fetch_all(
        f"""select name, downloads from software where category = '{type_name}' order by downloads desc limit 5"""
    )

    ret = dict(
        swap=swap,
        wallet=wallet,
        inquiry=inquiry,
        sociality=sociality,
        other=other,
        rank=rank,
        type_name=type_name,
    )

    return {"no_entity_software": ret}


async def software_prompt_mysql(id: int) -> dict:
    sd = await postgresql.fetch_all(
        query="""
            select android_url, win_url, mac_url, plugin_url, intro, long_intro, downloads
            from software where id = :id
        """,
        values={"id": id},
    )

    res_software = dict(sd[0])
    return {"software": res_software}


def format_datetime(dt: datetime.datetime | int) -> str:
    if isinstance(dt, int):
        dt = datetime.datetime.fromtimestamp(dt)
    return dt.strftime("%Y-%m-%d")


async def fetch_news(id: int) -> dict[Literal["human_analysis", "news"], list[dict]]:
    human_analysis, news = await asyncio.gather(
        postgresql.fetch_all(
            query="""
            SELECT n.title, n.updated_at, n.content
            FROM news n
            JOIN news_link_token nlk ON n.id = nlk.news_id
            WHERE n.title IS NOT NULL
                AND nlk.token_id = :id
                AND n.updated_at > (NOW() - INTERVAL '7 days')
                AND n.news_type_id IN (15, 16, 17)
            ORDER BY n.updated_at DESC
            LIMIT 1;
            """,
            values={"id": id},
        ),
        postgresql.fetch_all(
            query="""
            SELECT n.title, n.updated_at, n.content
            FROM news n
            JOIN news_link_token nlt ON n.id = nlt.news_id
            WHERE nlt.token_id = :id
            AND n.updated_at > NOW() - INTERVAL '7 days'
            ORDER BY n.updated_at DESC
            LIMIT 10;
            """,
            values={"id": id},
        ),
    )
    news.reverse()
    human_analysis.reverse()

    ret: dict = {
        "human_analysis": [],
        "news": [],
    }
    ret["human_analysis"] = list(
        {"title": i[0], "updated_at": format_datetime(i[1]), "content": i[2]}
        for i in human_analysis
    )
    ret["news"] = list(
        {"title": i[0], "updated_at": format_datetime(i[1]), "content": i[2]}
        for i in news
    )

    return ret


async def entity_prompt_api(entity: Entity) -> dict:
    # langu
    tasks: list[Coroutine[Any, Any, dict]] = []
    if entity.type == ENTITYTYPE2ID["coin"]:
        tasks.append(token_prompt_api(entity.id))
    if entity.type == ENTITYTYPE2ID["label"]:
        tasks.append(label_prompt_api(entity.id))
    if entity.type == ENTITYTYPE2ID["software"]:
        tasks.append(software_prompt_mysql(entity.id))

    results = await asyncio.gather(*tasks)

    dic = {}
    for i in results:
        dic.update(i)

    return dic



async def entities_prompt_api(entities: list[Entity]) -> list[Entity]:
    resps = await asyncio.gather(*(entity_prompt_api(entity) for entity in entities))
    for entity, resp in zip(entities, resps):
        entity.dynamic = resp
    return entities




async def no_entity_prompt_api(entity: No_entity) -> dict:
    # langu
    tasks: list[Coroutine[Any, Any, dict]] = []
    if entity.classify_type == NOENTITYTYPE2ID["coin"]:
        tasks.append(no_entity_token(entity.question))
    if entity.classify_type == NOENTITYTYPE2ID["label"]:
        tasks.append(no_entity_label(entity.question))
    if entity.classify_type == NOENTITYTYPE2ID["software"]:
        tasks.append(no_entity_software(entity.question))

    results = await asyncio.gather(*tasks)

    dic = {}
    for i in results:
        dic.update(i)

    return dic



async def entities_news(question: str, entities: list[Entity]) -> list[Entity]:
    resps = await asyncio.gather(
        *(get_active_infos_by_time(question, entity.id) for entity in entities)
    )
    for entity, resp in zip(entities, resps):
        entity.news = resp
    return entities



async def entities_news_by_embedding(
    question: str, entities: list[Entity]
) -> list[Entity]:
    resps = await asyncio.gather(
        *(
            get_active_infos_by_embedding(question=question, entity_id=entity.id)
            for entity in entities
        )
    )
    for entity, resp in zip(entities, resps):
        entity.vector_news = resp
    return entities
