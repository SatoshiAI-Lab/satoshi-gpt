import asyncio
import datetime
import random
from typing import Literal
from ai.embedding import get_embeddings
# from datasource.only_token_data import rule_data_filter
from models import Context, Entity

from db.postgre import postgresql
from models.models import Define_source, Reference
from utils.get_params import get_route_map_params



async def get_active_infos(
    entity_id: int, day: int = 14, is_origin: bool = False, only_twitter: bool = False
) -> list[Reference]:
    select = "select news.title, news.created_at, news.datetime_str, news.source, nlt.sentiment"
    news = await postgresql.fetch_all(
        query=f"""{select} FROM news
        JOIN news_link_token nlt ON nlt.news_id = news.id
        JOIN token t ON t.id = nlt.token_id
        WHERE t.id = :token_id
        AND news.created_at >= NOW() - INTERVAL ':day days'
        ORDER BY news.created_at DESC""",
        values={"token_id": entity_id, "day": day},
    )

    route_map = await postgresql.fetch_all(
        query="""select COALESCE(
        title->>'en',
        title->>'zh',
        title->>(ARRAY(SELECT json_object_keys(title) LIMIT 1))[0]
        ) || '\n' || COALESCE(
        content->>'en',
        content->>'zh',
        content->>(ARRAY(SELECT json_object_keys(content) LIMIT 1))[0]
        ) as title, tlrm.created_at, rm.estimated_time from route_map rm 
            join token_link_route_map tlrm on tlrm.route_map_id = rm.id
            where tlrm.token_id = :token_id
            order by rm.estimated_time desc""",
        values={"token_id": entity_id},
    )

    twitter_filter_query = (
        ""
        if is_origin
        else """ and (tn.laji is null or tn.laji = 0) and content_type = 'tweet' and not tn.content ->> 'en' like '%Current Price%' and not tn.content ->> 'en' like '%bitcoinprice%'"""
    )
    twitter = await postgresql.fetch_all(
        query=f"""
        SELECT COALESCE(
        content->>'en',
        content->>'zh',
        content->>(ARRAY(SELECT json_object_keys(tn.content) LIMIT 1))[0]
        ) as title,TO_TIMESTAMP(tn.published_at)::timestamp as published_at, tn.datetime_str, ('https://twitter.com/' || tn.twitter ||  '/status/' || tn.id) as source FROM twitter_news tn
            join token_link_twitter_news tltn on tltn.twitter_news_id = tn.id
            WHERE DATE(TO_TIMESTAMP(tn.published_at)) >= NOW() - INTERVAL ':day DAY'
                AND tltn.token_id = :token_id
                {twitter_filter_query}
            order by tn.published_at desc""",
        values={"token_id": entity_id, "day": day},
    )

    total_infos_dict: dict[
        Literal["twitter", "news", "announcement", "route_map"], list
    ] = {
        "news": [] if only_twitter else news,
        "route_map": [] if only_twitter else route_map,
        "twitter": twitter,
        "announcement": [],
    }
    print(
        "news_len:",
        len(news),
        "route_len:",
        len(route_map),
        "twitter_len:",
        len(twitter),
    )

    ret: list[Reference] = []
    for key, val in total_infos_dict.items():
        for i in val:
            ret.append(
                Reference(
                    type=key,
                    content=i[0] if i[0] else "",
                    published_at=i[1],
                    datetime_str=i[2],
                    url=i[3] if len(i) == 4 else "",
                    sentiment=i[4] if len(i) == 5 else None,
                )
            )

    # ret = rule_data_filter(ret)

    return ret


def get_informations_by_score(informations: list):
    index = 4

    total_length = 80 
    result_list = []
    score_4 = []
    score_3 = []
    score_2 = []
    score_1 = []
    score_0 = []

    for info in informations:
        if info[index] == 4 and len(score_4) < total_length / 2 + 1:
            result_list.append(info)
            score_4.append(info)

    for info in informations:
        if info[index] == 3 and len(score_3) < total_length / 2 + 1:
            result_list.append(info)
            score_3.append(info)

    if len(result_list) < total_length:
        left_supply = total_length - len(result_list)
        for info in informations:
            if info[index] == 2 and len(score_2) < left_supply:
                result_list.append(info)
                score_2.append(info)

    if len(result_list) < total_length:
        left_supply = total_length - len(result_list)
        for info in informations:
            if info[index] == 1 and len(score_1) < left_supply:
                result_list.append(info)
                score_1.append(info)

    if len(result_list) < total_length:
        left_supply = total_length - len(result_list)
        for info in informations:
            if info[index] == 0 and len(score_0) < left_supply:
                result_list.append(info)
                score_0.append(info)

    return result_list


async def get_active_infos_by_time(
    question: str, entity_id: int = 0
) -> list[Reference]:
    params = get_route_map_params(
        question
    )  
    news = []
    if params[1] != "future":
        news_entity_query = f" and nlt.token_id = {entity_id}" if entity_id != 0 else ""
        news_time_query = (
            "DATE(news.created_at) = CURRENT_DATE"
            if params[1] == "this" and params[2] == "day" and len(params) == 3
            else f"news.created_at >= NOW() - INTERVAL '{params[0]} days'"
        )

        sentiment_query = " and nlt.sentiment = 1" if "好" in question else ""
        sentiment_query = (
            " and nlt.sentiment = -1"
            if "坏" in question or "不好" in question
            else sentiment_query
        )
        sentiment_query = (
            ""
            if not "好" in question and not "坏" in question and not "不好" in question
            else sentiment_query
        )

        join_query = (
            "JOIN news_link_token nlt ON nlt.news_id = news.id"
            if news_entity_query
            else ""
        )
        join_query = (
            "JOIN news_link_token nlt ON nlt.news_id = news.id"
            if sentiment_query
            else join_query
        )

        news = await postgresql.fetch_all(
            query=f"""select news.title, news.created_at, news.datetime_str, news.source,news.score FROM news {join_query}
            WHERE {news_time_query}{news_entity_query}{sentiment_query} and is_similar_by_vec = 0
            ORDER BY news.created_at DESC"""
        )

        news = get_informations_by_score(news)

    route_map_entity_query = (
        f" and tlrm.token_id = {entity_id}" if entity_id != 0 else ""
    )
    route_map_time_query = {
        "pass": f"DATE(rm.estimated_time) >= NOW() - INTERVAL '{params[0]} DAY' and DATE(rm.estimated_time) <= NOW()",
        "future": f"DATE(rm.estimated_time) >= NOW() and DATE(rm.estimated_time) <= NOW() + INTERVAL '{params[0]} DAY'",
        "this": "DATE(rm.estimated_time) = CURRENT_DATE"
        if params[1] == "this" and params[2] == "day" and len(params) == 3
        else "DATE(rm.estimated_time) >= NOW() - INTERVAL ':pass_day DAY' and DATE(rm.estimated_time) <= NOW() + INTERVAL ':future_day DAY'",
    }
    route_map = await postgresql.fetch_all(
        query=f"""select COALESCE(
        title->>'en',
        title->>'zh',
        title->>(ARRAY(SELECT json_object_keys(title) LIMIT 1))[0]
        ) || '\n' || COALESCE(
        content->>'en',
        content->>'zh',
        content->>(ARRAY(SELECT json_object_keys(content) LIMIT 1))[0]
        ) as title, tlrm.created_at, rm.estimated_time from route_map rm 
            join token_link_route_map tlrm on tlrm.route_map_id = rm.id
            where {route_map_time_query[params[1]]}{route_map_entity_query}
            order by rm.estimated_time desc""",
        values={"pass_day": params[0], "future_day": params[3]}
        if len(params) == 4
        else {},
    )

    twitter = []
    twitter_entity_query = f" and tltn.token_id = {entity_id}" if entity_id != 0 else ""
    join_query = (
        "join token_link_twitter_news tltn on tltn.twitter_news_id = tn.id"
        if twitter_entity_query
        else ""
    )
    twitter_time_query = {
        "future": f"DATE(tn.datetime_str) >= NOW() and DATE(tn.datetime_str) <= NOW() + INTERVAL '{params[0]} DAY'",
        "this": "DATE(tn.datetime_str) = CURRENT_DATE"
        if params[1] == "this" and params[2] == "day" and len(params) == 3
        else "DATE(tn.datetime_str) >= NOW() - INTERVAL ':pass_day DAY' and DATE(tn.datetime_str) <= NOW() + INTERVAL ':future_day DAY'",
        "pass": f"TO_TIMESTAMP(tn.published_at) >= NOW() - INTERVAL '{params[0]} DAY'",
    }
    query = f"""SELECT COALESCE(
            content->>'en',
            content->>'zh',
            content->>(ARRAY(SELECT json_object_keys(tn.content) LIMIT 1))[0]
            ) as title,TO_TIMESTAMP(tn.published_at)::timestamp as published_at, tn.datetime_str, 
            ('https://twitter.com/' || tn.twitter ||  '/status/' || tn.id) as source,tn.score FROM twitter_news tn {join_query}
                WHERE {twitter_time_query[params[1]]}{twitter_entity_query}
                and (tn.laji is null or tn.laji = 0) and content_type = 'tweet'
                order by tn.datetime_str desc"""

    twitter = await postgresql.fetch_all(
        query=query,
        values={"pass_day": params[0], "future_day": params[3]}
        if len(params) == 4
        else {},
    )

    twitter = get_informations_by_score(twitter)

    total_infos_dict: dict[
        Literal["twitter", "news", "announcement", "route_map"], list
    ] = {
        "news": list(set(news))[:20],
        "route_map": list(set(route_map)),
        "twitter": list(set(twitter))[:10],
        "announcement": [],
    }

    ret: list[Reference] = []
    for key, val in total_infos_dict.items():
        for i in val:
            ret.append(
                Reference(
                    type=key,
                    content=i[0] if i[0] else "",
                    published_at=i[1],
                    datetime_str=i[2],
                    url=i[3] if len(i) == 4 else "",
                    sentiment=i[4] if len(i) == 5 else None,
                )
            )

    # ret = rule_data_filter(ret)

    return ret


async def get_active_infos_by_condition(
    ctx: Context,
    entity_id: int,
    day: int = 14,
    pass_future: Literal["pass", "future", "all"] = "all",
    sentiments: list[int] | None = None,
    include_sort: list[Define_source] | None = None,
    is_origin: bool = False,
) -> list[Reference]:
    if include_sort is None:
        include_sort = [
            Define_source(type="twitter"),
            Define_source(type="news"),
            Define_source(type="announcement"),
            Define_source(type="route_map"),
        ]
    if is_origin:
        ctx.only_token_news = await get_active_infos(
            entity_id=entity_id, day=day, is_origin=is_origin
        )

    filter_origin_data = []
    for t in include_sort:
        limit_num = 0
        for e in ctx.entities:
            for new in e.news:
                if new.type == t.type:
                    if t.limit != -1:
                        limit_num += 1
                        if limit_num > t.limit:
                            break
                    filter_origin_data.append(new)

    filter_sentiment_data = []
    if sentiments is None or len(sentiments) == 0:
        filter_sentiment_data = filter_origin_data
    else:
        for i in filter_origin_data:
            for s in sentiments:
                if i.sentiment == s:
                    filter_sentiment_data.append(i)

    filter_time_data = []
    if pass_future == "all":
        filter_time_data = filter_sentiment_data
    else:
        for i in filter_sentiment_data:
            if i.datetime_str is None:
                if pass_future == "future":
                    if i.published_at > datetime.datetime.now():
                        filter_time_data.append(i)

                if pass_future == "pass":
                    if (
                        i.published_at <= datetime.datetime.now()
                        and i.published_at
                        >= datetime.datetime.now() - datetime.timedelta(days=day)
                    ):
                        filter_time_data.append(i)
            else:
                if pass_future == "future":
                    if (
                        i.datetime_str > datetime.datetime.now()
                        and i.datetime_str
                        <= datetime.timedelta(days=day) + datetime.datetime.now()
                    ):
                        filter_time_data.append(i)

                if pass_future == "pass":
                    if (
                        i.datetime_str <= datetime.datetime.now()
                        and i.datetime_str
                        >= datetime.datetime.now() - datetime.timedelta(days=day)
                    ):
                        filter_time_data.append(i)


    return filter_time_data


def token_pass_news(entity_news: list[Reference]):
    pass_news = []
    for i in entity_news:
        if (
            isinstance(i.datetime_str, datetime.datetime)
            and i.datetime_str > datetime.datetime.now()
        ):
            continue
        pass_news.append(i)
    return pass_news


def token_future_news(entity_news: list[Reference]):
    future_news = []
    for i in entity_news:
        if (
            isinstance(i.datetime_str, datetime.datetime)
            and i.datetime_str > datetime.datetime.now()
        ):
            future_news.append(i)
    return future_news


def token_risk_news(entity_news: list[Reference]):
    risk_news = []
    for i in entity_news:
        if i.sentiment == -1:
            risk_news.append(i)
    return risk_news


async def get_news_by_embedding(
    embedding: list, similarity: float = 0.8, day: int = 999, entity_id: int = 0
):
    news_entity_query = "" if entity_id == 0 else f" and nlt.token_id = {entity_id}"
    news = await postgresql.fetch_all(
        f"""
        SELECT title, created_at, datetime_str,source,sentiment, similarity FROM (
            SELECT
                news.title,
                news.created_at,
                news.datetime_str,
                news.source,
                nlt.sentiment,
                1 - (news.title_vector <=> :vec) AS similarity
            FROM news JOIN news_link_token nlt on nlt.news_id = news.id
            where news.created_at > NOW() - INTERVAL ':day day' {news_entity_query}
            ORDER BY similarity DESC
        ) AS sub
        WHERE similarity > :similarity ORDER BY similarity DESC
        """,
        values={"vec": str(embedding[0]), "similarity": similarity, "day": day},
    )
    return news


async def get_route_map_by_embedding(
    embedding: list, similarity: float = 0.8, day: int = 999, entity_id: int = 0
):
    route_map = await postgresql.fetch_all(
        f"""
        SELECT title, created_at, estimated_time, similarity FROM (
            select COALESCE(
                title->>'en',
                title->>'zh',
                title->>(ARRAY(SELECT json_object_keys(title) LIMIT 1))[0]
                ) || '\n' || COALESCE(
                content->>'en',
                content->>'zh',
                content->>(ARRAY(SELECT json_object_keys(content) LIMIT 1))[0]
                ) as title, tlrm.created_at, rm.estimated_time,
                1 - (title_vector <=> :vec) AS similarity 
            FROM route_map rm join token_link_route_map tlrm on tlrm.route_map_id = rm.id
            ORDER BY similarity DESC
        ) AS sub
        WHERE similarity > :similarity
        """,
        values={"vec": str(embedding[0]), "similarity": similarity},
    )
    return route_map


async def get_twitter_by_embedding(
    embedding: list, similarity: float = 0.8, day: int = 999, entity_id: int = 0
):
    twitter_entity_query = "" if entity_id == 0 else f" and tltn.token_id = {entity_id}"
    twitter = await postgresql.fetch_all(
        f"""
        SELECT title, published_at, datetime_str, source, similarity FROM (
           SELECT COALESCE(
                content->>'en',
                content->>'zh',
                content->>(ARRAY(SELECT json_object_keys(tn.content) LIMIT 1))[0]
                ) as title,TO_TIMESTAMP(tn.published_at)::timestamp as published_at, tn.datetime_str, ('https://twitter.com/' || tn.twitter ||  '/status/' || tn.id) as source,
                1 - (content_vector <=> :vec) AS similarity 
            FROM twitter_news tn join token_link_twitter_news tltn on tltn.twitter_news_id = tn.id WHERE TO_TIMESTAMP(tn.published_at) > NOW() - INTERVAL ':day day' {twitter_entity_query}
            ORDER BY similarity DESC
        ) AS sub
        WHERE similarity > :similarity
        """,
        values={"vec": str(embedding[0]), "similarity": similarity, "day": day},
    )
    return twitter


def formate_to_reference(
    news: list = [], route_map: list = [], twitter: list = [], announcement: list = []
) -> list[Reference]:
    total_infos_dict: dict[
        Literal["twitter", "news", "announcement", "route_map"], list
    ] = {
        "news": news,
        "route_map": route_map,
        "twitter": twitter,
        "announcement": announcement,
    }

    ret: list[Reference] = []
    for key, val in total_infos_dict.items():
        for i in val:
            ret.append(
                Reference(
                    type=key,
                    content=i[0] if i[0] else "",
                    published_at=i[1],
                    datetime_str=i[2],
                    url=i[3] if len(i) == 5 else "",
                    sentiment=i[4] if len(i) == 6 else None,
                )
            )

    # ret = rule_data_filter(ret)

    return ret


async def get_active_infos_by_embedding(
    question: str,
    limit: int = 2,
    similarity: float = 0.8,
    entity_id: int = 0,
    day: int = 999,
) -> list[Reference]:
    embedding = await get_embeddings([question])

    news = await get_news_by_embedding(
        embedding=embedding, similarity=similarity, entity_id=entity_id, day=day
    )
    news_ref = formate_to_reference(news=news)
    news = news_ref[:limit]

    route_map = await get_route_map_by_embedding(
        embedding=embedding, similarity=similarity, entity_id=entity_id, day=day
    )
    route_map_ref = formate_to_reference(route_map=route_map)
    route_map = route_map_ref[:2]

    twitter = await get_twitter_by_embedding(
        embedding=embedding, similarity=similarity, entity_id=entity_id, day=day
    )
    twitter_ref = formate_to_reference(twitter=twitter)
    twitter = twitter_ref[:2]

    ret = news + route_map + twitter

    return ret
