transaction_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_transaction_info",
            "description": "Get complete transaction information",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_token": {
                        "type": "string",
                        "description": "The token that user wants to use to make transactions, e.g. BTC",
                    },
                    "from_amount": {
                        "type": "number",
                        "description": "The amount of token that the user wants to trade with",
                        "default": 0.01,
                    },
                    "to_token": {
                        "type": "string",
                        "description": "The token that user wants to obtain through transaction",
                    },
                },
                "required": ["from_token", "from_amount", "to_token"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_staking_info",
            "description": "Get complete staking token information",
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
            "name": "get_nft_info",
            "description": "Get complete nft transaction information",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]
transaction_system = "Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous.Please specify the amount of from_token you are willing to use for purchasing to_token. "
# "To proceed with your transaction, please specify the amount of from_token you are willing to use for purchasing to_token. "
# "The actual amount of BTC you can obtain will be calculated based on the current market rate."

wallet_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_chain_name",
            "description": "Get the name of chain in which the user wants to create a wallet,user must provide the name of chain",
            "parameters": {
                "type": "object",
                "properties": {
                    "chain_name": {
                        "type": "string",
                        "description": "The chain in which the user wants to create a wallet",
                    },
                },
                "required": ["chain_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_private_key_and_chain_name",
            "description": "Get the private key that the user wants to import, or user wants to import a wallet, they need to provide their private key",
            "parameters": {
                "type": "object",
                "properties": {
                    "private_key": {
                        "type": "string",
                        "description": "The private key that the user wants to import",
                    },
                    "chain_name": {
                        "type": "string",
                        "description": "The chain in which the user wants to import a wallet or private key",
                    },
                },
                "required": ["private_key", "chain_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wallet_list",
            "description": "If user wants to checkout their wallet list or he total amount of money in the wallet or which wallets they have",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]
# Please specify the chain in which the user wants to create a wallet.
wallet_system = "Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous.The current version only supports creating wallets for Solana and ETH chains.Do not mention the security issues related to the private key."


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
            "name": "make_transaction",
            "description": "User wants to make transactions, Optional,user can provides the amount they wish to trade",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "The amount of token that the user wants to trade with",
                        "minimum": 0.000000001,
                        "default":0
                    },
                },
                "required": ["amount"],
            },
        },
    },
]
contract_system = "Reply as concise as possible, no more than 20 words."

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
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "subscript_pools",
    #         "description": "Subscribe to or monitor pools",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {},
    #             "required": [],
    #         },
    #     },
    # },
]
subscript_system = "Ask for clarification if a user request is ambiguous.If user hasn't specified what they want to subscribe to/monitor(news/wallet address/twitter/exchange),you should ask for clarification.Reply as concise as possible, no more than 20 words."

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
