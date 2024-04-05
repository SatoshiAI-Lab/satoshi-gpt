from typing import Literal
from pydantic import BaseModel
from apis import app
from db.postgre import postgresql
from models import Reference
import datetime


def get_title_en(item):
    try:
        content_str = item[0]["en"]
    except KeyError:
        content_str = item[0]["zh"]

    if item[2]:
        content_str += "\n" + item[2]
    return content_str


async def get_twitter_by_token_links_mysql(
    token_id: int,
    day: int = 7,
    query_type: Literal["default", "only_twitter", "datetime", "origin"] = "default",
) -> list[Reference]:
    select = """
        SELECT
            tn.content,
            tn.published_at,
            tn.external_content_summary,
            tn.datetime_str,
            tn.id,
            tn.twitter,
            tn.tweets_id
    """
    query_default = f"""
        {select}
        FROM twitter_news tn
        join token_link_twitter_news tltn on tltn.twitter_news_id = tn.id
        WHERE DATE(TO_TIMESTAMP(tn.published_at)) >= NOW() - INTERVAL ':day DAY'
            AND tltn.token_id = :token_id
            and (tn.laji is null or tn.laji = 0)
            and content_type = 'tweet'
            and not tn.content ->> 'en' like '@%'
            and not tn.content ->> 'en' like 'RT @%'
            and not tn.content ->> 'en' like '%Current Price%'
            and not tn.content ->> 'en' like '%bitcoinprice%' 
        order by tn.published_at desc;
    """
    query_origin = f"""
        {select}
        FROM twitter_news tn
        join token_link_twitter_news tltn on tltn.twitter_news_id = tn.id
        WHERE DATE(TO_TIMESTAMP(tn.published_at)) >= NOW() - INTERVAL ':day DAY'
            AND tltn.token_id = :token_id
        order by tn.published_at desc;
    """
    query_datetime = f"""
        {select}
        FROM twitter_news tn
        WHERE DATE(TO_TIMESTAMP(published_at)) >= NOW() - INTERVAL ':day DAY'
            and (laji is null or laji = 0)
            and not tn.content ->> 'en' like '@%'
            and not tn.content ->> 'en' like 'RT @%'
            and datetime_str is null
        order by published_at desc;
    """
    query_list = {
        "default": query_default,
        "only_twitter": query_default,
        "origin": query_origin,
        "datetime": query_datetime,
    }
    res_raw = await postgresql.fetch_all(
        query=query_list[query_type],
        values={"day": day}
        if query_type == "datetime"
        else {"token_id": token_id, "day": day},
    )
    twitter_recent_data: list[Reference] = []
    for item in res_raw:
        content_str = get_title_en(item)
        datetime_format = datetime.datetime.fromtimestamp(item[1])
        # datetime_item = datetime_format.strftime("%Y-%m-%d %H:%M:%S")

        twitter_recent_data.append(
            Reference(
                id=item[4],
                type="twitter",
                content=content_str,
                published_at=datetime_format,
                datetime_str=item[3],
                url=f"https://twitter.com/{item[5]}/status/{item[6]}",
            )
        )
        # twitter_recent_data.append([content_str, datetime_format, item[3]])

    return twitter_recent_data


class Update_datetime(BaseModel):
    twitter_news_id: int
    datetime_str: str | None
    update_type: Literal["twitter", "announcement"]


@app.post("/update_datetime_str_single")
async def update_datetime_str_mysql(query: Update_datetime):
    update_type_str = (
        "twitter_news"
        if query.update_type == "twitter" or query.update_type == "twitter_news"
        else "announcement"
    )
    update_query = f"""
    update {update_type_str} set datetime_str = :datetime_str where id = :twitter_news_id
    """
    try:
        await postgresql.execute(
            query=update_query,
            values={
                "datetime_str": query.datetime_str,
                "twitter_news_id": query.twitter_news_id,
            },
        )
        return {
            "status": 200,
            "message": "success",
            "twitter_id": query.twitter_news_id,
        }
    except Exception as e:
        return {"status": 502, "message": e, "twitter_id": query.twitter_news_id}
