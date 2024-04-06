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
                        "minimum": 0.000000001,
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

create_wallet_tools = [
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
create_wallet_system = "Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous.The current version only supports creating wallets for Solana and ETH chains.Do not mention the security issues related to the private key."
