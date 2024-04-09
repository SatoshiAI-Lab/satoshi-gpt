transaction_tools = [
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_transaction_info",
    #         "description": "Get complete transaction information",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "from_token": {
    #                     "type": "string",
    #                     "description": "The token that user wants to use to make transactions, only support from token is SOL, default from_token is SOL",
    #                     "default": "SOL",
    #                 },
    #                 "from_amount": {
    #                     "type": "number",
    #                     "description": "The amount of token that the user wants to trade with.",
    #                     "default": 0.01,
    #                 },
    #                 "to_token": {
    #                     "type": "string",
    #                     "description": "The token that user wants to obtain through transaction",
    #                 },
    #             },
    #             "required": ["from_token", "from_amount", "to_token"],
    #         },
    #     },
    # },
    {
        "type": "function",
        "function": {
            "name": "get_buy_coin_name",
            "description": "Get the name of the token the user wants to buy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "buy_coin_name": {
                        "type": "string",
                        "description": "The name of the coin the user wants to buy.",
                    },
                    "from_amount": {
                        "type": "number",
                        "description": "The amount of token that the user wants to trade with.",
                        "default": 0.01,
                    },
                },
                "required": ["buy_coin_name", "from_amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sell_coin_name",
            "description": "Get the name of the token the user wants to buy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sell_coin_name": {
                        "type": "string",
                        "description": "Retrieve the name of the token the user wants to sell.",
                    },
                },
                "required": ["sell_coin_name"],
            },
        },
    },
]
transaction_system = "Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous. U is USDT."
# "To proceed with your transaction, please specify the amount of from_token you are willing to use for purchasing to_token. "
# "The actual amount of BTC you can obtain will be calculated based on the current market rate."

wallet_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_chain_name",
            "description": "Get the name of chain in which the user wants to create a wallet,user can provide the name of chain or the default chain name is SOL",
            "parameters": {
                "type": "object",
                "properties": {
                    "chain_name": {
                        "type": "string",
                        "description": "The chain in which the user wants to create a wallet",
                        "default": "SOL",
                    },
                },
                "required": ["chain_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wallet_list",
            "description": "If users want to view their list of wallets or know which wallets they have or check out the balances of wallets.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "delete_wallet",
    #         "description": "If user wants to delete one of their wallets, user must provides the wallet name that the user wants to delete",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "wallet_name": {
    #                     "type": "string",
    #                     "description": "The name of wallet that the user wants to delete",
    #                 },
    #             },
    #             "required": ["wallet_name"],
    #         },
    #     },
    # },
    {
        "type": "function",
        "function": {
            "name": "change_wallet_name",
            "description": "If a user wants to change the name of the wallet, they must provide the current name of the wallet and the desired new name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_name": {
                        "type": "string",
                        "description": "The current name of the wallet. Attention: Users may directly provide the wallet name. Please include 'wallet name' directly, without excluding words similar to 'wallet.'",
                    },
                    "new_name": {
                        "type": "string",
                        "description": "The new wallet name that the user wants to change to.",
                    },
                },
                "required": ["current_name", "new_name"],
            },
        },
    },
]
# Please specify the chain in which the user wants to create a wallet.
wallet_system = "Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous.The current version only supports creating wallets for Solana and ETH chains."


import_export_tools = [
    {
        "type": "function",
        "function": {
            "name": "import_private_key",
            "description": "Get the private key that the user wants to import, or user wants to import a wallet, they need to provide their private key",
            "parameters": {
                "type": "object",
                "properties": {
                    "private_key": {
                        "type": "string",
                        "description": "The private key that the user wants to import",
                    },
                    # "chain_name": {
                    #     "type": "string",
                    #     "description": "The chain in which the user wants to import a wallet or private key,if user do not provide,default chain name is SOL",
                    #     "default": "SOL",
                    # },
                },
                "required": ["private_key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_private_key",
            "description": "Retrieves the wallet name for exporting the private key. If the wallet name is not provided, the user will be prompted to supply one.",
            "parameters": {
                "type": "object",
                "properties": {
                    "wallet_name": {
                        "type": "string",
                        "description": "The wallet name for which the user wants to export the private key. If not provided, the user will be asked to provide it.",
                    },
                },
                "required": ["wallet_name"],
            },
        },
    },
]
# Do not mention the security issues related to the private key.
import_export_system = "Ask for clarification if a user request is ambiguous.Reply as concise as possible, no more than 20 words."

subscript_tools = [
    {
        "type": "function",
        "function": {
            "name": "subscript_news",
            "description": "User wants to enable or disable news monitoring.",
            "parameters": {
                "type": "object",
                "properties": {
                    "switch": {
                        "type": "string",
                        "description": "User wants to enable or disable news monitoring. Subscription is enabled by default.",
                        "enum": ["on", "off"],
                        "defaule": "on",
                    }
                },
                "required": ["switch"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subscript_wallet_address",
            "description": "Subscribe to or monitor a wallet address",
            "parameters": {
                "type": "object",
                "properties": {
                    "wallet_address": {
                        "type": "string",
                        "description": "The wallet address that the user wants to subscribe to or monitor.",
                    }
                },
                "required": ["wallet_address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subscript_twitter",
            "description": "Subscribe to or monitor twitter",
            "parameters": {
                "type": "object",
                "properties": {
                    "people_name": {
                        "type": "string",
                        "description": "The twitter of people who user wants to subscribe or monitor to.",
                        "enum": ["Elon Musk", "Vitalik", "CZ", "Binance", "Coinbase"],
                    }
                },
                "required": ["people_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subscript_exchange_announcement",
            "description": "User wants to monitor or subscribe to announcement from exchange.",
            "parameters": {
                "type": "object",
                "properties": {
                    "exchange_name": {
                        "type": "string",
                        "description": "The exchange that users wants to subscribe to or monitor.",
                        "enum": [
                            "okx",
                            "mexc",
                            "huobi",
                            "bitget",
                            "coinbase-exchange",
                            "kraken",
                            "gate.io",
                            "bithumb",
                            "kucoin",
                            "binance",
                            "upbit",
                        ],
                    }
                },
                "required": ["exchange_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subscript_pool",
            "description": "Subscribe to or monitor pool",
            "parameters": {
                "type": "object",
                "properties": {
                    "pool_name": {
                        "type": "string",
                        "description": "The name of the pool that the user wants to monitor",
                        "enum": [
                            "Solana",
                            "Ethereum",
                            "BSC",
                            "Optimism",
                            "BASE",
                            "Arbitrum",
                        ]
                    }
                },
                "required": ["pool_name"],
            },
        },
    },
]
subscript_system = "Ask for clarification if a user request is ambiguous.If user hasn't specified what they want to subscribe to/monitor(news/wallet address/twitter/exchange),you should ask for clarification.Reply as concise as possible, no more than 20 words."


contract_tools = [
    {
        "type": "function",
        "function": {
            "name": "only_contract_address",
            "description": "User only provides a contract address,without any further information",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buying_transaction",
            "description": "User wants to make a transaction for buying",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_amount": {
                        "type": "number",
                        "description": "The amount of token that the user wants to trade with.",
                        "default": 0.01,
                    }
                },
                "required": ["from_amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "selling_transaction",
            "description": "User wants to make a transaction for selling",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "make_transaction",
    #         "description": "User wants to make transactions, Optional,user can provides the amount they wish to trade",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "amount": {
    #                     "type": "number",
    #                     "description": "The amount of token that the user wants to trade with",
    #                     "minimum": 0.000000001,
    #                     "default": 0,
    #                 },
    #             },
    #             "required": ["amount"],
    #         },
    #     },
    # },
    {
        "type": "function",
        "function": {
            "name": "monitor_address",
            "description": "The user wants to monitor or subscript the address.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]
# Do not mention the security issues related to the private key.
contract_system = "Reply as concise as possible, no more than 20 words."
