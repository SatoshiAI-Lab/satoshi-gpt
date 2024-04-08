import asyncio
import json
from typing import Literal
from ai.GPT import (
    gpt_gen_template_stream,
    gpt_gen_template_text,
    gpt_tools_no_stream,
)
from apis.intent_api import create_wallet_api, import_private_key_api, wallet_list_api,get_wallet_balance
from datasource.active_infos import (
    get_active_infos_by_embedding,
    get_active_infos_by_time,
)
from datasource.history import get_history_intent
from datasource.knowledge import get_knowledge
from datasource.entities import (
    entities_news_by_embedding,
    entities_prompt_api,
    no_entity_prompt_api,
    entities_news,
)
from datasource.tools_news_future import get_future_main
from datasource.tools_news_recent import get_recent_situation
from ai.reference import add_references, clear_references

from logic import prepare
from logic import token_info_fetch
from datasource.tools_news_fluctuation import get_news_analysis_main
from utils.change_text import extract_first_number
from utils.check_data import check_which_subscript, find_contract_address_solana, is_single_token_query 
from models.models import (
    ENTITYID2TYPE,
    ENTITYID2TYPE_EN,
    Context,
    Entity,
    No_entity,
    ResponseChunk,
)

from prompts.tools import (
    transaction_tools,
    transaction_system,
    wallet_tools,
    wallet_system,
    contract_system,
    contract_tools,
    import_export_system,
    import_export_tools,
    subscript_tools,
    subscript_system
)
from utils import mult_lang
from utils.get_data import get_class_by_question, get_exchange_id, get_people_twitter_id, get_wallet_id_by_wallet_name, get_wallet_list_by_token_contract, get_wallet_list_have_sol

async def question_event(ctx: Context):
    intent_history = []
    solana_contract: str | None = None
    
    if ctx.intent_stream and ctx.intent_stream.startswith("intent_stream"):
        res_classify = str(ctx.intent_stream)[-1]
        intent_history, ctx.intent_stream = await get_history_intent(
            ctx.global_.uuid, ctx.intent_stream
        )

    if ctx.intent_stream == "intent_history":
        intent_history, ctx.intent_stream = await get_history_intent(
            ctx.global_.uuid, ctx.intent_stream
        )
    
    if not ctx.intent_stream.startswith("intent_stream"):
        solana_contract = find_contract_address_solana(ctx.question)
        wallet_balances = get_class_by_question(ctx.question)
        if solana_contract:  
            res_classify = "6"
        elif wallet_balances: 
            res_classify = "3"
            ctx.question = wallet_balances
        else:
            classify_num = await gpt_gen_template_text(
                ctx, "gpt_classify_intent_or_not"
            )
            res_classify = extract_first_number(classify_num)

    
    if res_classify == "2":
        
        tools_res = await gpt_tools_no_stream(
            transaction_system, ctx.question, transaction_tools, intent_history
        )
        if "tool_calls" in tools_res:
            if tools_res.tool_calls[0].function.name == "get_buy_coin_name":
                from_token = "SOL"
                from_amount = 0

                to_token = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "buy_coin_name"
                ]

                try:
                    from_amount = json.loads(
                        tools_res.tool_calls[0].function.arguments
                    )["from_amount"]
                except:
                    from_amount = 0

                
                to_token = "USDT" if to_token.upper == "U" else to_token

                
                if (
                    "SOL" == to_token.upper()
                    or "SOLANA" == to_token.upper()
                    or "索拉" in to_token
                ):
                    yield ResponseChunk(
                        answer_type="do_not_support_buy_token",
                        text=mult_lang.intent[ctx.global_.language]["transaction"][
                            "do_not_support_buy_token"
                        ],
                        meta={
                            "type": "do_not_support_buy_token",
                            "status": 200,
                            "data": {},
                        },
                    )
                    return

                
                wallet_list_res = await wallet_list_api(
                    access_token=ctx.global_.access_token
                )

                
                if not wallet_list_res["status"] == 200:
                    yield ResponseChunk(
                        answer_type="get_wallet_wrong",
                        text=mult_lang.intent[ctx.global_.language]["contract"][
                            "transaction_fail"
                        ],
                        meta={
                            "type": "contract_transaction_fail",
                            "status": wallet_list_res["status"],
                            "data": wallet_list_res["data"],
                        },
                    )
                    return

                if len(wallet_list_res["data"]) < 1:
                    yield ResponseChunk(
                        answer_type="chat_stream",
                        text=mult_lang.intent[ctx.global_.language]["wallet"][
                            "do_not_have_wallet"
                        ],
                        meta={"type": "", "status": 200, "data": {}},
                    )
                    return
                
                have_sol_wallets = get_wallet_list_have_sol(wallet_list_res["data"])
                
                if not have_sol_wallets:
                    yield ResponseChunk(
                        answer_type="chat_stream",
                        text=mult_lang.intent[ctx.global_.language]["transaction"][
                            "do_not_have_sol"
                        ],
                        meta={
                            "type": "wallet_list",
                            "status": 200,
                            "data": {},
                        },
                    )
                    return
                
                to_token_contract = await prepare.get_token_contract_by_name(to_token)

                if not to_token_contract:
                    yield ResponseChunk(
                        answer_type="chat_stream",
                        text=mult_lang.intent[ctx.global_.language][
                            "wrong_token_name"
                        ].format(to_token),
                    )
                    return

                yield ResponseChunk(
                    answer_type="transaction_confirm_stream",
                    text=mult_lang.intent[ctx.global_.language]["contract"][
                        "transaction_confirm"
                    ],
                    meta={
                        "type": "transaction_confirm_buy",
                        "status": 200,
                        "data": {
                            "from_token_name": "SOL",
                            "from_token_contract": "So11111111111111111111111111111111111111112",
                            "amount": from_amount,
                            "to_token_name": to_token,
                            "to_token_contract": to_token_contract,
                            "match_wallets": [],
                            "address_filter": [
                                "11111111111111111111111111111111",
                                "So11111111111111111111111111111111111111112",
                            ],
                            "chain_filter": {"platform": "SOL", "chain_name": "Solana"},
                        },
                    },
                )
                return

            if tools_res.tool_calls[0].function.name == "get_sell_coin_name":
                to_token = "SOL"
                to_amount = 0

                from_token = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "sell_coin_name"
                ]

                
                from_token = "USDT" if from_token.upper == "U" else from_token

                
                if (
                    "SOL" == from_token.upper()
                    or "SOLANA" == from_token.upper()
                    or "索拉" in from_token
                ):
                    yield ResponseChunk(
                        answer_type="do_not_support_sell_token",
                        text=mult_lang.intent[ctx.global_.language]["transaction"][
                            "do_not_support_sell_token"
                        ],
                        meta={
                            "type": "do_not_support_sell_token",
                            "status": 200,
                            "data": {},
                        },
                    )
                    return

                
                wallet_list_res = await wallet_list_api(
                    access_token=ctx.global_.access_token
                )

                
                if not wallet_list_res["status"] == 200:
                    yield ResponseChunk(
                        answer_type="get_wallet_wrong",
                        text=mult_lang.intent[ctx.global_.language]["contract"][
                            "transaction_fail"
                        ],
                        meta={
                            "type": "contract_transaction_fail",
                            "status": wallet_list_res["status"],
                            "data": wallet_list_res["data"],
                        },
                    )
                    return

                
                if len(wallet_list_res["data"]) < 1:
                    yield ResponseChunk(
                        answer_type="chat_stream",
                        text=mult_lang.intent[ctx.global_.language]["wallet"][
                            "do_not_have_wallet"
                        ],
                        meta={"type": "", "status": 200, "data": {}},
                    )
                    return

                
                from_token_contract = await prepare.get_token_contract_by_name(
                    from_token
                )

                
                if not from_token_contract:
                    yield ResponseChunk(
                        answer_type="chat_stream",
                        text=mult_lang.intent[ctx.global_.language][
                            "wrong_token_name"
                        ].format(to_token),
                    )
                    return

                
                match_wallets = get_wallet_list_by_token_contract(
                    from_token_contract, wallet_list_res["data"]
                )

                
                if not match_wallets:
                    yield ResponseChunk(
                        answer_type="do_not_have_token",
                        text=mult_lang.intent[ctx.global_.language]["transaction"][
                            "do_not_have_token"
                        ],
                        meta={
                            "type": "wallet_list",
                            "status": 200,
                            "data": {},
                        },
                    )
                    return

                
                yield ResponseChunk(
                    answer_type="transaction_confirm_stream",
                    text=mult_lang.intent[ctx.global_.language]["contract"][
                        "transaction_confirm"
                    ],
                    meta={
                        "type": "transaction_confirm_sell",
                        "status": 200,
                        "data": {
                            "from_token_name": from_token,
                            "from_token_contract": from_token_contract,
                            "amount": to_amount,
                            "to_token_name": "SOL",
                            "to_token_contract": "So11111111111111111111111111111111111111112",
                            "match_wallets": [],
                            "address_filter": [from_token_contract],
                            "chain_filter": {"platform": "SOL", "chain_name": "Solana"},
                        },
                    },
                )
                return

        else:
            yield ResponseChunk(
                answer_type="intent_stream_2",
                text=tools_res.content,
            )
            return

    
    if res_classify == "3" or res_classify == "0":
        
        tools_res = await gpt_tools_no_stream(
            wallet_system, ctx.question, wallet_tools, intent_history
        )

        if "tool_calls" in tools_res:
            
            if tools_res.tool_calls[0].function.name == "get_chain_name":
                chain_name = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "chain_name"
                ]

                format_chain_name = prepare.get_format_chain_name(str(chain_name))
                if not format_chain_name:
                    yield ResponseChunk(
                        answer_type="intent_stream_3",
                        text=mult_lang.intent[ctx.global_.language][
                            "wrong_chain_name"
                        ].format(chain_name),
                        meta={
                            "type": "wrong_chain_name",
                            "status": 401,
                            "data": {"message": "Only support SOL and EVM"},
                        },
                    )
                    return
                
                create_res = await create_wallet_api(
                    format_chain_name, ctx.global_.access_token
                )

                text = (
                    mult_lang.intent[ctx.global_.language]["wallet"][
                        "create_success"
                    ].format(create_res["data"]["name"], create_res["data"]["address"])
                    if create_res["status"] == 200
                    else mult_lang.intent[ctx.global_.language]["wallet"]["create_fail"]
                )
                type_str = "wallet_list" if create_res["status"] == 200 else ""
                
                yield ResponseChunk(
                    answer_type="intent_stream_0",
                    text=text,
                    meta={
                        "type": type_str,
                        "status": create_res["status"],
                        "data": [create_res["data"]],
                    },
                )
                return

            if tools_res.tool_calls[0].function.name == "get_wallet_list":
                
                wallet_list_res = await wallet_list_api(
                    access_token=ctx.global_.access_token
                )

                if wallet_list_res["status"] == 200:
                    if len(wallet_list_res["data"]) >= 1:
                        text = mult_lang.intent[ctx.global_.language]["wallet"][
                            "wallet_list_success"
                        ]
                        type_str = "wallet_list"
                    else:
                        text = mult_lang.intent[ctx.global_.language]["wallet"][
                            "do_not_have_wallet"
                        ]
                        type_str = ""
                else:
                    text = mult_lang.intent[ctx.global_.language]["wallet"][
                        "wallet_list_fail"
                    ]
                    type_str = "get_wallet_list_wrong"

                yield ResponseChunk(
                    answer_type="wallet_list_stream",
                    text=text,
                    meta={
                        "type": type_str,
                        "status": wallet_list_res["status"],
                        "data": wallet_list_res["data"],
                    },
                )
                return

            if tools_res.tool_calls[0].function.name == "change_wallet_name":
                current_name = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "current_name"
                ]
                new_name = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "new_name"
                ]

                wallet_list_res = await wallet_list_api(
                    access_token=ctx.global_.access_token
                )

                if not wallet_list_res["status"] == 200:
                    yield ResponseChunk(
                        answer_type="intent_stream_3",
                        text=mult_lang.intent[ctx.global_.language]["wallet"][
                            "update_wallet_name_fail"
                        ],
                        meta={
                            "type": "get_wallet_list_wrong",
                            "status": wallet_list_res["status"],
                            "data": wallet_list_res["data"],
                        },
                    )
                    return

                wallet_id = get_wallet_id_by_wallet_name(
                    current_name, wallet_list_res["data"]
                )
                if not wallet_id:
                    yield ResponseChunk(
                        answer_type="intent_stream_3",
                        text=mult_lang.intent[ctx.global_.language][
                            "wrong_wallet_name"
                        ],
                        meta={
                            "type": "change_name_wallet_list",
                            "status": 200,
                            "data": wallet_list_res["data"],
                        },
                    )
                    return
                
                update_wallet_name_res = await update_wallet_name_api(
                    ctx.global_.access_token, wallet_id, new_name
                )
                text = (
                    mult_lang.intent[ctx.global_.language]["wallet"][
                        "update_wallet_name_success"
                    ].format(current_name, update_wallet_name_res["data"]["name"])
                    if update_wallet_name_res["status"] == 200
                    else mult_lang.intent[ctx.global_.language]["wallet"][
                        "update_wallet_name_fail"
                    ]
                )
                
                yield ResponseChunk(
                    answer_type="update_wallet_name_stream",
                    text=text,
                    meta={
                        "type": "",
                        "status": update_wallet_name_res["status"],
                        "data": update_wallet_name_res["data"],
                    },
                )
                return

    
    if res_classify == "4":
        tools_res = await gpt_tools_no_stream(
            import_export_system, ctx.question, import_export_tools, intent_history
        )

        if "tool_calls" in tools_res:
            if tools_res.tool_calls[0].function.name == "import_private_key":
                private_key = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "private_key"
                ]
                chain_name = "SOL"

                format_chain_name = prepare.get_format_chain_name(chain_name)
                if not format_chain_name:
                    yield ResponseChunk(
                        answer_type="intent_stream_4",
                        text=mult_lang.intent[ctx.global_.language][
                            "wrong_chain_name"
                        ].format(chain_name),
                    )
                    return

                import_res = await import_private_key_api(
                    ctx.global_.access_token,
                    private_key,
                    format_chain_name,
                )
                text = (
                    mult_lang.intent[ctx.global_.language]["wallet"][
                        "import_success"
                    ].format(import_res["data"]["name"], import_res["data"]["address"])
                    if import_res["status"] == 200
                    else mult_lang.intent[ctx.global_.language]["wallet"]["import_fail"]
                )

                wallet_list_res = await wallet_list_api(
                    access_token=ctx.global_.access_token
                )
                type_str = "wallet_list" if wallet_list_res["status"] == 200 else ""
                yield ResponseChunk(
                    answer_type="import_wallet_stream",
                    text=text,
                    meta={
                        "type": type_str,
                        "status": wallet_list_res["status"],
                        "data": wallet_list_res["data"],
                    },
                )
                return

            if tools_res.tool_calls[0].function.name == "export_private_key":
                wallet_name = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "wallet_name"
                ]

                wallet_list_res = await wallet_list_api(
                    access_token=ctx.global_.access_token
                )

                if not wallet_list_res["status"] == 200:
                    yield ResponseChunk(
                        answer_type="intent_stream_4",
                        text=mult_lang.intent[ctx.global_.language]["wallet"][
                            "export_private_key_fail"
                        ],
                        meta={
                            "type": "",
                            "status": wallet_list_res["status"],
                            "data": wallet_list_res["data"],
                        },
                    )
                    return

                wallet_id = get_wallet_id_by_wallet_name(
                    wallet_name, wallet_list_res["data"]
                )
                if not wallet_id:
                    yield ResponseChunk(
                        answer_type="intent_stream_4",
                        text=mult_lang.intent[ctx.global_.language][
                            "wrong_wallet_name"
                        ],
                        meta={
                            "type": "export_wallet_list",
                            "status": wallet_list_res["status"],
                            "data": wallet_list_res["data"],
                        },
                    )
                    return

                export_res = await export_private_key_api(
                    ctx.global_.access_token, wallet_id
                )
                text = (
                    mult_lang.intent[ctx.global_.language]["wallet"][
                        "export_private_key_success"
                    ].format(wallet_name, export_res["data"]["private_key"])
                    if export_res["status"] == 200
                    else mult_lang.intent[ctx.global_.language]["wallet"][
                        "export_private_key_fail"
                    ]
                )
                yield ResponseChunk(
                    answer_type="export_private_key_stream",
                    text=text,
                    meta={
                        "type": "",
                        "status": export_res["status"],
                        "data": export_res["data"],
                    },
                )
                return

        else:
            yield ResponseChunk(
                answer_type="intent_stream_4",
                text=tools_res.content,
            )
            return

    
    if res_classify == "5":
        tools_res = await gpt_tools_no_stream(
            subscript_system, ctx.question, subscript_tools, intent_history
        )

        if "tool_calls" in tools_res:
            if tools_res.tool_calls[0].function.name == "subscript_news":
                switch = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "switch"
                ]
                subscript_res = await create_subscription(
                    ctx.global_.access_token, 0, {"switch": switch}
                )

                if subscript_res["status"] == 200:
                    switch_str = (
                        "news_success" if switch == "on" else "news_cancel_success"
                    )
                    text = mult_lang.intent[ctx.global_.language]["subscript"][
                        switch_str
                    ]
                else:
                    text = mult_lang.intent[ctx.global_.language]["subscript"][
                        "news_success"
                    ]

                yield ResponseChunk(
                    answer_type="subscript_news",
                    text=text,
                )
                return

            if tools_res.tool_calls[0].function.name == "subscript_wallet_address":
                wallet_address = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "wallet_address"
                ]
                trade_params = [{"address": wallet_address, "name": "", "chain": "SOL"}]
                subscript_res = await create_subscription(
                    ctx.global_.access_token, 3, trade_params
                )
                if subscript_res["status"] == 200:
                    text = mult_lang.intent[ctx.global_.language]["subscript"][
                        "wallet_address_success"
                    ]
                    meta_type = "subscript_wallet_address_success"
                else:
                    text = mult_lang.intent[ctx.global_.language]["subscript"][
                        "wallet_address_fail"
                    ]
                    meta_type = "subscript_wallet_address_fail"

                yield ResponseChunk(
                    answer_type="subscript_wallet_address",
                    text=text,
                    meta={"type": meta_type, "status": 200, "data": []},
                )
                return

            if tools_res.tool_calls[0].function.name == "subscript_twitter":
                people_name = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "people_name"
                ]
                twitter_id, all_people = get_people_twitter_id(people_name)

                subscript_res = await create_subscription(
                    ctx.global_.access_token, 1, [twitter_id]
                )

                if subscript_res["status"] == 200:
                    text = mult_lang.intent[ctx.global_.language]["subscript"][
                        "twitter_success"
                    ].format("people_name")
                    meta_type = ""
                    data = []
                else:
                    text = mult_lang.intent[ctx.global_.language]["subscript"][
                        "twitter_fail"
                    ]
                    meta_type = "twitter_people_list"
                    data = all_people

                yield ResponseChunk(
                    answer_type="subscript_twitter",
                    text=text,
                    meta={"type": meta_type, "status": 200, "data": data},
                )
                return

            if (
                tools_res.tool_calls[0].function.name
                == "subscript_exchange_announcement"
            ):
                exchange_name = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "exchange_name"
                ]

                exchange_id, all_exchanges = get_exchange_id(exchange_name)

                subscript_res = await create_subscription(
                    ctx.global_.access_token, 2, [exchange_id]
                )

                if subscript_res["status"] == 200:
                    text = mult_lang.intent[ctx.global_.language]["subscript"][
                        "exchange_success"
                    ].format(exchange_name)
                    meta_type = ""
                    data = []
                else:
                    text = mult_lang.intent[ctx.global_.language]["subscript"][
                        "exchange_fail"
                    ]
                    meta_type = "exchanges_announcement_list"
                    data = all_exchanges

                yield ResponseChunk(
                    answer_type="subscript_announcement",
                    text=text,
                    meta={"type": meta_type, "status": 200, "data": data},
                )
                return

        else:
            check_res = check_which_subscript(ctx.question)
            data = {}
            meta_type = ""
            if check_res:
                data = mult_lang.intent[ctx.global_.language]["subscript_list"][
                    check_res
                ]
                meta_types = {
                    "twitter": "subscript_twitter_list",
                    "exchange": "subscript_announcement_list",
                    "news": "",
                    "pool": "",
                    "trade": "",
                }
                meta_type = meta_types[check_res]

            yield ResponseChunk(
                answer_type="intent_stream_5",
                text=tools_res.content,
                meta={
                    "type": meta_type,
                    "status": 200,
                    "data": [i for i in data.keys()],
                },
            )

        return

    
    if res_classify == "6":
        
        wallet_list_res = await wallet_list_api(access_token=ctx.global_.access_token)

        if not wallet_list_res["status"] == 200:
            yield ResponseChunk(
                answer_type="get_wallet_wrong",
                text=mult_lang.intent[ctx.global_.language]["contract"][
                    "transaction_fail"
                ],
                meta={
                    "type": "contract_transaction_fail",
                    "status": wallet_list_res["status"],
                    "data": wallet_list_res["data"],
                },
            )
            return

       
        if len(wallet_list_res["data"]) < 1:
           
            create_res = await create_wallet_api("Solana", ctx.global_.access_token)
            if not create_res["status"] == 200:
                create_res = await create_wallet_api("Solana", ctx.global_.access_token)
                wallet_name = create_res["data"]["name"]
                wallet_address = create_res["data"]["address"]

            wallet_name = create_res["data"]["name"]
            wallet_address = create_res["data"]["address"]

            yield ResponseChunk(
                answer_type="chat_stream",
                text=mult_lang.intent[ctx.global_.language]["create_token"][
                    "create_confirm"
                ],
                meta={
                    "type": "create_token_no_wallet",
                    "status": 200,
                    "data": {
                        "wallet_name": wallet_name,
                        "wallet_address": wallet_address,
                    },
                },
            )
            return

        yield ResponseChunk(
            answer_type="chat_stream",
            text=mult_lang.intent[ctx.global_.language]["create_token"][
                "create_confirm"
            ],
            meta={"type": "create_token_have_wallet", "status": 200, "data": {}},
        )
        return

        
    if res_classify == "7":
        if not solana_contract:
            yield ResponseChunk(
                answer_type="wrong_contract",
                text=mult_lang.intent[ctx.global_.language]["wrong_contract"],
                meta={
                    "type": "no_contract_address",
                    "status": 200,
                    "data": {}
                },
            )
            return
        
        tools_res = await gpt_tools_no_stream(
                contract_system, ctx.question, contract_tools, intent_history
        )

        if "tool_calls" in tools_res:
            
            if tools_res.tool_calls[0].function.name == "only_contract_address":

                wallet_balance = await get_wallet_balance(
                    ctx.global_.access_token, solana_contract
                )
                if not wallet_balance["status"] == 200:
                    yield ResponseChunk(
                        answer_type="wrong_contract",
                        text=mult_lang.intent[ctx.global_.language]["wrong_contract"],
                        meta={
                            "type": "",
                            "status": wallet_balance["status"],
                            "data": wallet_balance["data"],
                        },
                    )
                    return

                yield ResponseChunk(
                    answer_type="intent_history",  
                    text=mult_lang.intent[ctx.global_.language]["contract"][
                        "contract_balance"
                    ],
                    meta={
                        "type": "contract_wallet_balance",
                        "status": wallet_balance["status"],
                        "data": wallet_balance["data"],
                    },
                )
                return

         
            if tools_res.tool_calls[0].function.name == "buying_transaction":
                from_token = "SOL"
                from_amount = 0
                
                from_amount = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "from_amount"
                ]
                

                
                if (
                    solana_contract == "So11111111111111111111111111111111111111112"
                    or solana_contract == "11111111111111111111111111111111"
                ):
                    yield ResponseChunk(
                        answer_type="do_not_support_buy_token",
                        text=mult_lang.intent[ctx.global_.language]["transaction"][
                            "do_not_support_buy_token"
                        ],
                        meta={
                            "type": "do_not_support_buy_token",
                            "status": 200,
                            "data": {},
                        },
                    )
                    return

                
                wallet_list_res = await wallet_list_api(
                    access_token=ctx.global_.access_token
                )

                
                if not wallet_list_res["status"] == 200:
                    yield ResponseChunk(
                        answer_type="get_wallet_wrong",
                        text=mult_lang.intent[ctx.global_.language]["contract"][
                            "transaction_fail"
                        ],
                        meta={
                            "type": "contract_transaction_fail",
                            "status": wallet_list_res["status"],
                            "data": wallet_list_res["data"],
                        },
                    )
                    return

                
                if len(wallet_list_res["data"]) < 1:
                    yield ResponseChunk(
                        answer_type="chat_stream",
                        text=mult_lang.intent[ctx.global_.language]["wallet"][
                            "do_not_have_wallet"
                        ],
                        meta={"type": "", "status": 200, "data": {}},
                    )
                    return

                
                have_sol_wallets = get_wallet_list_have_sol(wallet_list_res["data"])

                
                if not have_sol_wallets:
                    yield ResponseChunk(
                        answer_type="chat_stream",
                        text=mult_lang.intent[ctx.global_.language]["transaction"][
                            "do_not_have_sol"
                        ],
                        meta={
                            "type": "wallet_list",
                            "status": 200,
                            "data": {},
                        },
                    )
                    return

                
                token_info = await get_coin_info(
                    ctx.global_.access_token, solana_contract, "Solana"
                )
                if not token_info["status"] == 200:
                    yield ResponseChunk(
                        answer_type="wrong_contract",
                        text=mult_lang.intent[ctx.global_.language]["wrong_contract"],
                        meta={
                            "type": "",
                            "status": token_info["status"],
                            "data": token_info["data"],
                        },
                    )
                    return

                symbol = token_info["data"]["symbol"]

                yield ResponseChunk(
                    answer_type="transaction_confirm_stream",
                    text=mult_lang.intent[ctx.global_.language]["contract"][
                        "transaction_confirm"
                    ],
                    meta={
                        "type": "transaction_confirm_buy",
                        "status": 200,
                        "data": {
                            "from_token_name": "SOL",
                            "from_token_contract": "So11111111111111111111111111111111111111112",
                            "amount": from_amount,
                            "to_token_name": symbol,
                            "to_token_contract": solana_contract,
                            "match_wallets": [],
                            "address_filter": [
                                "11111111111111111111111111111111",
                                "So11111111111111111111111111111111111111112",
                            ],
                            "chain_filter": {"platform": "SOL", "chain_name": "Solana"},
                        },
                    },
                )
                return

            
            if tools_res.tool_calls[0].function.name == "selling_transaction":
                to_token = "SOL"
                to_amount = 0

                
                if solana_contract == "So11111111111111111111111111111111111111112":
                    yield ResponseChunk(
                        answer_type="do_not_support_sell_token",
                        text=mult_lang.intent[ctx.global_.language]["transaction"][
                            "do_not_support_sell_token"
                        ],
                        meta={
                            "type": "do_not_support_sell_token",
                            "status": 200,
                            "data": {},
                        },
                    )
                    return

                
                wallet_list_res = await wallet_list_api(
                    access_token=ctx.global_.access_token
                )

                
                if not wallet_list_res["status"] == 200:
                    yield ResponseChunk(
                        answer_type="get_wallet_wrong",
                        text=mult_lang.intent[ctx.global_.language]["contract"][
                            "transaction_fail"
                        ],
                        meta={
                            "type": "contract_transaction_fail",
                            "status": wallet_list_res["status"],
                            "data": wallet_list_res["data"],
                        },
                    )
                    return

                
                if len(wallet_list_res["data"]) < 1:
                    yield ResponseChunk(
                        answer_type="chat_stream",
                        text=mult_lang.intent[ctx.global_.language]["wallet"][
                            "do_not_have_wallet"
                        ],
                        meta={"type": "", "status": 200, "data": {}},
                    )
                    return

                
                match_wallets = get_wallet_list_by_token_contract(
                    solana_contract, wallet_list_res["data"]
                )

                
                if not match_wallets:
                    yield ResponseChunk(
                        answer_type="do_not_have_token",
                        text=mult_lang.intent[ctx.global_.language]["transaction"][
                            "do_not_have_token"
                        ],
                        meta={
                            "type": "wallet_list",
                            "status": 200,
                            "data": {},
                        },
                    )
                    return

                
                token_info = await get_coin_info(
                    ctx.global_.access_token, solana_contract, "Solana"
                )
                if not token_info["status"] == 200:
                    yield ResponseChunk(
                        answer_type="wrong_contract",
                        text=mult_lang.intent[ctx.global_.language]["wrong_contract"],
                        meta={
                            "type": "",
                            "status": token_info["status"],
                            "data": token_info["data"],
                        },
                    )
                    return

                
                symbol = token_info["data"]["symbol"]

                yield ResponseChunk(
                    answer_type="transaction_confirm_stream",
                    text=mult_lang.intent[ctx.global_.language]["contract"][
                        "transaction_confirm"
                    ],
                    meta={
                        "type": "transaction_confirm_sell",
                        "status": 200,
                        "data": {
                            "from_token_name": symbol,
                            "from_token_contract": solana_contract,
                            "amount": to_amount,
                            "to_token_name": "SOL",
                            "to_token_contract": "So11111111111111111111111111111111111111112",
                            "match_wallets": [],
                            "address_filter": [solana_contract],
                            "chain_filter": {"platform": "SOL", "chain_name": "Solana"},
                        },
                    },
                )
                return

            
            if tools_res.tool_calls[0].function.name == "monitor_address":
                trade_params = [
                    {"address": solana_contract, "name": "", "chain": "Solana"}
                ]
                subscript_res = await create_subscription(
                    ctx.global_.access_token, 3, trade_params
                )
                if subscript_res["status"] == 200:
                    text = mult_lang.intent[ctx.global_.language]["subscript"][
                        "wallet_address_success"
                    ]
                    meta_type = "subscript_wallet_address_success"
                else:
                    text = mult_lang.intent[ctx.global_.language]["subscript"][
                        "wallet_address_fail"
                    ]
                    meta_type = "subscript_wallet_address_fail"

                yield ResponseChunk(
                    answer_type="subscript_wallet_address",
                    text=text,
                    meta={"type": meta_type, "status": 200, "data": []},
                )
                return

        else:
            yield ResponseChunk(
                answer_type="intent_history",
                text=tools_res.content,
                meta={
                    "type": "",
                    "status": 200,
                    "data": [],
                },
            )
            return


    inter_resp, ctx.entities = prepare.entity_extract(ctx)
    if inter_resp:
        meta = inter_resp.model_dump()
        for e in meta.get("entities", []):
            if "dynamic" in e:
                e["dynamics"] = e["dynamic"]
                del e["dynamic"]
            e["type_name"] = ENTITYID2TYPE[e["type"]]

        meta_front: dict[str, list] = {}
        for e in meta.get("entities", []):
            type_name = ENTITYID2TYPE_EN[e["type"]]
            if not meta_front.get(type_name):
                meta_front[type_name] = []
            meta_front[type_name].append(e)

        yield ResponseChunk(
            answer_type="interactive",
            meta=meta_front,
        )
        yield ResponseChunk(answer_type="end")

        return

    if single_entity := is_single_token_query(ctx):
        async for i in token_info_fetch.get_prompt_data(ctx, single_entity):
            yield i
        return

    have_entity_record = "no entity"
    if ctx.entities:
        have_entity_record = "have entity"

        if ctx.global_.language == "en":
            market_cup_keys = ["market cap", "inflation", "selling pressure", "lock value", "tvl"]
            circulation_keys = ["circulation", "total supply", "supply"]
        else:
            market_cup_keys = ["市值", "年通胀", "通胀率", "释放", "抛压", "总锁定价值", "tvl"]
            circulation_keys = ["流通量", "总量", "供应量"]
        add_info_dict: dict[
            str,
            Literal[
                "emtity",
                "market",
                "circulation",
                "active",
                "price",
                "plan",
                "risk",
                "invest",
                "compare",
                "other",
                "exchange",
            ],
        ] = {
            "1": "active",
            "2": "price",
            "3": "plan",
            "4": "risk",
            "5": "invest",
            "6": "compare",
            "7": "other",
            "8": "exchange",
            "14": "other",
        }

        for e in ctx.entities:
            if e.type == 1:
                for k in market_cup_keys:
                    if k in ctx.question.lower():
                        ctx.add_information_type.append("market")

                for k in circulation_keys:
                    if k in ctx.question:
                        ctx.add_information_type.append("circulation")

        ctx.entities = await entities_prompt_api(ctx.entities)
        ctx.entities = await entities_news(ctx.question, ctx.entities)
        ctx.entities = await entities_news_by_embedding(ctx.question, ctx.entities)
        classify_num, ctx.knowledges = await asyncio.gather(
            gpt_gen_template_text(ctx, "gpt_classify_have_entity"),
            get_knowledge(ctx.question),
        )

        res_classify = extract_first_number(classify_num)

        ctx.add_information_type.append(add_info_dict[res_classify])

        ctx.add_information_type = list(set(ctx.add_information_type))

        if res_classify == "8":
            gpt_result = await gpt_gen_template_text(
                ctx=None,
                template="get_exchange_parameter",
                question=ctx.question,
            )
            yield ResponseChunk(answer_type="exchange_stream", text="好的，正在为您处理，请稍等...")
            yield ResponseChunk(answer_type="exchange_stream", meta=gpt_result)
            return

        async for i in await gpt_gen_template_stream(ctx, "have_entity_other"):
            yield i

        have_token = False
        token_entity: Entity = Entity(id=1, name="BTC", type=1)
        for e in ctx.entities:
            if e.type == 1:
                have_token = True
                token_entity = e

        for a in ctx.add_information_type:
            if a == "active" and have_token:
                yield ResponseChunk(answer_type="chat_stream", text="\n\n")

                async for i in get_news_analysis_main(
                    ctx,
                    token_entity.id,
                    ctx.global_.language,
                ):
                    yield i

                async for i in get_recent_situation(ctx, token_entity, True):
                    yield i

                yield ResponseChunk(answer_type="chat_stream", text="\n\n")
                for e in ctx.entities:
                    if e.type == 1 and not e.name.upper() == "SEC":
                        async for i in await gpt_gen_template_stream(
                            ctx, "token_price_and_fluctuation", prompt=e.dynamic
                        ):
                            yield i

            if a == "price" and have_token:
                yield ResponseChunk(answer_type="chat_stream", text="\n\n")
                for e in ctx.entities:
                    if e.type == 1 and not e.name.upper() == "SEC":
                        async for i in await gpt_gen_template_stream(
                            ctx, "token_price_and_fluctuation", prompt=e.dynamic
                        ):
                            yield i
                        yield ResponseChunk(answer_type="chat_stream", text="\n\n")

            if a == "plan" and have_token:
                yield ResponseChunk(answer_type="chat_stream", text="\n\n")
                async for i in get_future_main(ctx, token_entity):
                    yield i

            if a == "risk" and have_token:
                yield ResponseChunk(answer_type="chat_stream", text="\n\n")
                async for i in token_info_fetch.risk_analysis(
                    ctx=ctx,
                    single_entity=token_entity,
                    token_symbol=token_entity.name,
                    can_hide=True,
                ):
                    if i.answer_type == "risk_analysis_hide":
                        yield ResponseChunk(
                            answer_type="risk_analysis_stream", text="暂无相关风险"
                        )
                        continue

                    yield i

            if a == "market" and have_token:
                for e in ctx.entities:
                    yield ResponseChunk(answer_type="chat_stream", text="\n\n")
                    if e.type == 1:
                        async for i in await gpt_gen_template_stream(
                            ctx, "token_market_value", prompt=e.dynamic
                        ):
                            yield i

            if a == "circulation" and have_token:
                for e in ctx.entities:
                    yield ResponseChunk(answer_type="chat_stream", text="\n\n")
                    if e.type == 1:
                        async for i in await gpt_gen_template_stream(
                            ctx, "token_circulation_and_total_amount", prompt=e.dynamic
                        ):
                            yield i

    else:
        (
            classify_num,
            ctx.knowledges,
            ctx.no_entity_news,
            ctx.no_entity_vector_news,
        ) = await asyncio.gather(
            gpt_gen_template_text(ctx, "gpt_classify_no_entity"),
            get_knowledge(ctx.question),
            get_active_infos_by_time(ctx.question),
            get_active_infos_by_embedding(ctx.question),
        )

        res_classify = extract_first_number(classify_num)

        if res_classify == "1" or res_classify == "2" or res_classify == "3":
            prompt = await no_entity_prompt_api(
                No_entity(classify_type=int(res_classify), question=ctx.question)
            )
            async for i in await gpt_gen_template_stream(
                ctx, "no_entity_basic", prompt=prompt
            ):
                yield i
            return

        if res_classify == "4":
            reference_list = ctx.no_entity_news + ctx.no_entity_vector_news
            yield add_references(reference_list)

            async for i in await gpt_gen_template_stream(ctx, "route_map_template"):
                yield i

            yield clear_references()
            return

        if res_classify == "5" or res_classify == "6" or res_classify == "7":
            async for i in await gpt_gen_template_stream(ctx, "no_entity_basic"):
                yield i

        if res_classify == "8":
            async for i in await gpt_gen_template_stream(ctx, "no_entity_basic"):
                yield i

    return
