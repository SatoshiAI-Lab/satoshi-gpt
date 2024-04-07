import re
from datasource.news_pg import get_news_by_name, get_news_pg
from models import ENTITYTYPE2ID, Entity, Context, Reference

def is_single_token_query(ctx: Context) -> Entity | None:
    if not len(ctx.entities) == 1:
        return None
    entity = ctx.entities[0]

    if not entity.type == ENTITYTYPE2ID["coin"]:
        return None

    test_question = ctx.question.strip().lower()

    remove_keys: list[str] = [
       
    ]
    for key in remove_keys:
        test_question = test_question.replace(key, "").strip()

    for name in entity.alias + [entity.name]:
        if test_question == name.lower():
            return entity

    return None


async def filter_entitiy_get_news(ctx: Context):

    name_list = []
    for e in ctx.entities:
        if e.type == 3:
            for name in e.dynamic["news_names"]:
                name_list.append(name)
        if e.type == 4 or e.type == 5:
            name_list.append(e.name)

    key_search_res = []
    for name in name_list:
        key_search: list[Reference] = await get_news_by_name(name)
        key_search_res += key_search

    if key_search_res:
        news_vec = await get_news_pg(ctx.question, 2, 0.78)
    else:
        news_vec = await get_news_pg(ctx.question, 6, 0.78)

    return key_search_res + news_vec


def check_is_pass_map(question: str):
    pass_key = []
    for i in pass_key:
        if i in question:
            return True

    return False


def has_contract_address_solana(input_string):
    solana_pattern = r"\b[A-HJ-NP-Za-km-z1-9]{32,44}\b"
    if re.search(solana_pattern, input_string):
        return True
    else:
        return False


def find_contract_address_solana(input_string):
    pattern = r"\b[A-HJ-NP-Za-km-z1-9]{32,44}\b"
    match = re.search(pattern, input_string)
    if match:
        return match.group(0)   
    else:
        return None

def check_which_subscript(input_str: str):
    subscript_class = {
        ("twitter", "推特"): "twitter",
        ("wallet", "钱包"): "trade",
        ("news", "新闻"): "news",
        ("cex", "dex", "exchange", "announcement", "公告", "交易所"): "exchange",
        ("pool", "池子"): "pool",
    }

    for key, value in subscript_class.items():
        for k in key:
            if k in input_str:
                return value

    return None