import re
from models.models import Context


def get_alias_few_shot(ctx: Context):
    alias_few_shot = ""
    for item in ctx.entities:
        alias_few_shot += item.name + "alias:" + ",".join(item.alias) + "\n"
    return alias_few_shot


def get_wallet_id_by_wallet_name(wallet_name: str, wallet_list: list):
    for item in wallet_list:
        if item["name"].lower() == wallet_name.lower():
            return item["id"]

    return None

def get_wallet_list_have_sol(wallet_list: list):
    ret_wallet_list = []
    for wallet in wallet_list:
        for token in wallet["tokens"]:
            if token["symbol"] and token["name"]:
                if (
                    token["symbol"].upper() == "SOL"
                    and token["name"].upper() == "SOLANA"
                    and token["amount"] > 0
                ):
                    ret_wallet_list.append(wallet)

    return ret_wallet_list


def get_wallet_list_by_token_contract(token_contract: str, wallet_list: list):
    ret_wallet_list = []
    for wallet in wallet_list:
        for token in wallet["tokens"]:
            if token["address"] == token_contract:
                ret_wallet_list.append(wallet)

    return ret_wallet_list

def get_class_by_question(question: str):
    wallet = ["balance", "余额"]

    if wallet[0] in question:
        return "wallet balances"

    if wallet[1] in question:
        return "钱包余额"

    return None


def get_wallet_list_have_sol(wallet_list: list):
    ret_wallet_list = []
    for wallet in wallet_list:
        for token in wallet["tokens"]:
            if token["symbol"] and token["name"]:
                if (
                    token["symbol"].upper() == "SOL"
                    and token["name"].upper() == "SOLANA"
                    and token["amount"] > 0
                ):
                    ret_wallet_list.append(wallet)

    return ret_wallet_list

def get_wallet_id_by_question(question: str, wallet_list: list):
    for item in wallet_list:
        if item["name"].lower() in question.lower():
            return item["id"], item["name"]

    return None, None


def get_the_chain_wallet_list(chain_name: str, wallet_list: list):
    pattern = r"\((.*?)\)"
    match = re.search(pattern, chain_name)
    chain_name = match.group(1) if match else chain_name

    ret_wallet_list = []
    for item in wallet_list:
        if item["platform"].lower() == chain_name.lower():
            ret_wallet_list.append(item)
    return ret_wallet_list, chain_name


def get_people_twitter_id(people_name: str, lang: str = "en"):

    people_ids = {
        ("Elon Musk", "马斯克"): "44196397",
        ("Vitalik", "V神"): "295218901",
        ("CZ", "赵长鹏"): "902926941413453824",
        ("Binance", "币安"): "877807935493033984",
        ("Coinbase", "Coinbase"): "574032254",
    }

    key_index = 0 if lang.lower() == "en" else 1

    for key, value in people_ids.items():
        if people_name.lower() == key[0].lower():
            return value, [i[key_index] for i in people_ids.keys()]
        if people_name.lower() == key[1].lower():
            return value, [i[key_index] for i in people_ids.keys()]

    return None, [i[key_index] for i in people_ids.keys()]


def get_exchange_id(exchange: str, lang: str = "en"):

    exchange_ids = {
        "okx": 10,
        "mexc": 56,
        "huobi": 99,
        "bitget": 111,
        "coinbase-exchange": 118,
        "kraken": 128,
        "gate.io": 156,
        "bithumb": 174,
        "kucoin": 176,
        "binance": 260,
        "upbit": 320,
    }

    for key, value in exchange_ids.items():
        if exchange.lower() == key.lower():
            return value, [i for i in exchange_ids.keys()]

    return None, [i for i in exchange_ids.keys()]


