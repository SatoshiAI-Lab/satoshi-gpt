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
from utils.check_data import find_contract_address_solana, is_single_token_query 
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
    create_wallet_tools,
    create_wallet_system,
    contract_system,
    contract_tools
)
from utils import mult_lang

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
        if solana_contract:  
            res_classify = "6"
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
            if tools_res.tool_calls[0].function.name == "get_transaction_info":
                
                from_token = "SOL"
                from_amount = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "from_amount"
                ]
                to_token = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "to_token"
                ]
                
                (
                    from_token_contract,
                    to_token_contract,
                ) = await prepare.get_token_contract(from_token, to_token)
                if not from_token_contract:
                    yield ResponseChunk(
                        answer_type="chat_stream",
                        text=mult_lang.intent[ctx.global_.language][
                            "wrong_token_name"
                        ].format(from_token),
                    )
                    return
                if not to_token_contract:
                    yield ResponseChunk(
                        answer_type="chat_stream",
                        text=mult_lang.intent[ctx.global_.language][
                            "wrong_token_name"
                        ].format(to_token),
                    )
                    return

                meta = {
                    "from_token_contract": from_token_contract,
                    "from_token_name": from_token,
                    "from_amount": from_amount,
                    "to_token_contract": to_token_contract,
                    "to_token_name": to_token,
                }

                yield ResponseChunk(
                    answer_type="transaction_stream",
                    text=mult_lang.intent[ctx.global_.language]["transaction"][
                        "confirm"
                    ].format(from_amount, from_token, to_token),
                    meta={"status": 200, "data": meta},
                )
                return

            
            if tools_res.tool_calls[0].function.name == "get_staking_info":
                yield ResponseChunk(
                    answer_type="chat_stream",
                    text="comming soon...",
                )
                return
            
            if tools_res.tool_calls[0].function.name == "get_nft_info":
                yield ResponseChunk(
                    answer_type="chat_stream",
                    text="comming soon...",
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
        yield ResponseChunk(
            answer_type="chat_stream",
            text="NFT server is comming soon",
        )
        return

    
    if res_classify == "5":
        
        tools_res = await gpt_tools_no_stream(
            create_wallet_system, ctx.question, create_wallet_tools, intent_history
        )

        if "tool_calls" in tools_res:
            
            if tools_res.tool_calls[0].function.name == "get_chain_name":
                chain_name = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "chain_name"
                ]

                
                format_chain_name = prepare.get_format_chain_name(str(chain_name))
                if not format_chain_name:
                    yield ResponseChunk(
                        answer_type="intent_stream_4",
                        text=mult_lang.intent[ctx.global_.language][
                            "wrong_chain_name"
                        ].format(chain_name),
                    )
                    return

                
                create_res = await create_wallet_api(
                    format_chain_name, ctx.global_.access_token
                )
                text = (
                    mult_lang.intent[ctx.global_.language]["wallet"][
                        "create_success"
                    ].format(create_res["data"]["address"])
                    if create_res["status"] == 200
                    else mult_lang.intent[ctx.global_.language]["wallet"]["create_fail"]
                )

                
                yield ResponseChunk(
                    answer_type="create_wallet_stream",
                    text=text,
                    meta=create_res["data"],
                )
                return

            
            if (
                tools_res.tool_calls[0].function.name
                == "get_private_key_and_chain_name"
            ):
                private_key = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "private_key"
                ]
                chain_name = json.loads(tools_res.tool_calls[0].function.arguments)[
                    "chain_name"
                ]
                
                
                
                format_chain_name = prepare.get_format_chain_name(str(chain_name))
                if not format_chain_name:
                    yield ResponseChunk(
                        answer_type="intent_stream_4",
                        text=mult_lang.intent[ctx.global_.language][
                            "wrong_chain_name"
                        ].format(chain_name),
                    )
                    return

                
                import_res = await import_private_key_api(
                    private_key, format_chain_name, ctx.global_.access_token
                )
                
                text = (
                    mult_lang.intent[ctx.global_.language]["wallet"][
                        "import_success"
                    ].format(import_res["data"]["address"])
                    if import_res["status"] == 200
                    else mult_lang.intent[ctx.global_.language]["wallet"]["import_fail"]
                )
                
                
                yield ResponseChunk(
                    answer_type="import_wallet_stream",
                    text=text,
                    meta=import_res["data"],
                )
                return

            
            if tools_res.tool_calls[0].function.name == "get_wallet_list":
                
                wallet_list_res = await wallet_list_api(
                    access_token=ctx.global_.access_token
                )
                text = (
                    mult_lang.intent[ctx.global_.language]["wallet"][
                        "wallet_list_success"
                    ]
                    if wallet_list_res["status"] == 200
                    else mult_lang.intent[ctx.global_.language]["wallet"][
                        "wallet_list_fail"
                    ]
                )
                
                yield ResponseChunk(
                    answer_type="wallet_list_stream", text=text, meta=wallet_list_res
                )
                return
        else:
            yield ResponseChunk(
                answer_type="intent_stream_4",
                text=tools_res.content,
            )
            return

    
    if res_classify == "6":
        
        if solana_contract:
            token_info = await prepare.get_token_by_contract(solana_contract)
            if token_info:
                name, symbol, price, percent_change_24_h = token_info
                percent_change_24_h = round(percent_change_24_h[0], 2)
                yield ResponseChunk(
                    answer_type="contract_stream",
                    text=f"{name[0]}({symbol[0]}), ${price[0]},  {percent_change_24_h}%",
                    meta={
                        "contract": solana_contract,
                        "token_name": name[0],
                        "token_symbol": symbol[0],
                        "price": price[0],
                        "percent_change_24_h": percent_change_24_h,
                    },
                )

        yield ResponseChunk(
            answer_type="chat_stream",
            text="wrong solana contract address",
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
