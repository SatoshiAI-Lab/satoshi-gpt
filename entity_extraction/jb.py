import asyncio
import jieba
import re
import json
import tqdm
import platform
from models import Entity, Item
from utils.beautify_text import beautifyText
from .init_data import (
    download_block_list,
    download_tokens,
    download_labels,
    download_software,
    download_people,
    download_economy,
)
import os


def get_temp_dir():
    if platform.system() == "Windows":
        temp_dir = os.path.join(os.environ["HOMEPATH"], ".cache", "satoshitools")
    else:
        temp_dir = os.path.join(os.environ["HOME"], ".cache", "satoshitools")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir


def clean(l: list[str]) -> list[str]:
    return [i.strip() for i in l if i.strip()]


confuse_list: set[str] = {
    "SAM",
    "IDO",
    "BIT",
    "SPACE",
    "DAO",
    "PRIME",
    "ARK",
    "CHAIN",
    "BRIDGE",
    "OPTIMISM",
    "ID",
    "DISNEY",
    "GUARDIAN",
    "SMART",
    "WHITE",
    "KEEP",
}

block_list: set[str] = {
    "XAI",
    "GROK",
    "MOVE",
    "NEW",
    "POW",
    "POS",
    "ETP",
    "ETF",
    "MINT",
    "DDOS",
    "ALPHA",
    "BETA",
    "NFT",
    "MEV",
    "KOL",
    "L2",
    "LABS",
    "AA",
    "LAYER",
    "VR",
    "AR",
    "MR",
    "AI",
    "DEFI",
    "DEX",
    "CEX",
    "DPI",
    "CPI",
    "GDP",
    "BUY",
    "SELL",
    "WOID",
    "BBC",
    "ABC",
    "CNN",
    "AP",
    "AFP",
    "UPI",
    "TASS",
    "TOP",
    "GEAR",
    "MEME",
    "PRE",
    "CORE",
    "VISION",
    "META",
    "PRO",
    "REAL",
    "ZER",
    "CLOUD",
    "PAY",
    "COIN",
    "MUSK",
    "ELON",
    "FLASH",
    "BITS",
    "BYTE",
    "BYTES",
    "DAPP",
    "DAPPS",
    "EAR",
    "STAKE",
    "LEND",
    "SWAP",
    "META",
    "STACK",
    "ZREO",
    "ONE",
    "TWO",
    "THREE",
    "FOUR",
    "FIVE",
    "SIX",
    "SEVEN",
    "EIGHT",
    "NINE",
    "TEN",
    "TOWER",
    "CEO",
    "ERC20",
    "WALLET",
    "BLOCK",
    "SAFE",
    "OPEN",
    "CLOSE",
    "FOR",
    "CHANGE",
    "TRADE",
}


class JB:
    def __init__(self) -> None:
        self.cache_entities_json = os.path.join(get_temp_dir(), "entities.json")
        self.cache_entities_block_json = os.path.join(
            get_temp_dir(), "entities_block.json"
        )

        self.dict = {}

        self.name_to_id: dict[str, list[str]] = {}

        self.multilang_name_to_id: dict[str, list[int]] = {}

        self.block_list: list[str] = []

    async def reload(self):
        self.dict = {}
        self.name_to_id = {}
        self.block_list = []
        await asyncio.gather(self.download_entities_dict(), self.download_block_list())
        await self.load_dict()

    async def load_dict(self):

        if self.dict:
            return

        if not os.path.exists(self.cache_entities_json) or not os.path.exists(
            self.cache_entities_block_json
        ):
            print("No cache file found, downloading from database...")
            await asyncio.gather(
                self.download_entities_dict(), self.download_block_list()
            )

        print("Loading entities dict...")
        with open(self.cache_entities_json, "r", encoding="utf-8") as f:
            j = json.loads(f.read())
        with open(self.cache_entities_block_json, "r", encoding="utf-8") as f:
            self.block_list = json.loads(f.read())

        self.dict = j

        for id in j:
            entity = j[id]
            for name in entity["alias"]:
                if not name:
                    continue

                name = name.upper()

                if self.is_multilang(name):
                    if name not in self.multilang_name_to_id:
                        self.multilang_name_to_id[name] = []

                    self.multilang_name_to_id[name].append(id)

                if name not in self.name_to_id:
                    self.name_to_id[name] = []

                self.name_to_id[name].append(id)

        for k in self.dict.keys():
            alias = j[k]["alias"]
            for name in alias:
                if not name:
                    continue
                if " " in name:
                    continue
                name = name.upper()
                jieba.add_word(name, freq=39)

        print(f"loaded {len(self.dict)} entities")

    def is_multilang(self, name: str) -> bool:
        return (
            bool(
                re.search(r"[\u4e00-\u9fa5]+", name)
                and re.search(r"[a-zA-Z0-9]+", name)
            )
            or " " in name
            or "." in name
            or "-" in name
        )

    def is_english(self, name: str) -> bool:
        return bool(re.search(r"[a-zA-Z0-9]+", name))

    async def download_block_list(self):
        block_list = await download_block_list()
        with open(os.path.join(get_temp_dir(), "entities_block.json"), "w") as f:
            f.write(json.dumps(block_list, ensure_ascii=True))

    async def download_entities_dict(self):

        print("Downloading entities from database...")
        entities = {}

        response: list[Entity] = []
        for r in await asyncio.gather(
            download_tokens(),
            download_labels(),
            download_software(),
            download_people(),
            download_economy(),
        ):
            response.extend(r)

        for entity in tqdm.tqdm(response):
            id = f"{entity.type}_{entity.id}"
            entities[id] = {
                "type": entity.type,
                "id": entity.id,
                "name": entity.name,
                "alias": entity.alias,
                "dynamic": entity.dynamic,
            }

        with open(self.cache_entities_json, "w", encoding="utf-8") as f:
            f.write(json.dumps(entities, ensure_ascii=True))

        return entities

    def cut(self, text: str) -> list[str]:

        text = text.upper()

        found_intervals = []
        for name in sorted(
            self.multilang_name_to_id.keys(), key=lambda x: len(x), reverse=True
        ):
            begin: int = text.find(name)
            end: int = begin + len(name)

            if begin == -1:
                continue

            if (
                begin != 0
                and self.is_english(text[begin - 1])
                and self.is_english(text[begin])
            ):
                continue
            if (
                end != len(text)
                and self.is_english(text[end - 1])
                and self.is_english(text[end])
            ):
                continue

            found_intervals.append((begin, end))

        found_intervals.sort(key=lambda x: x[0])

        non_overlapping_intervals: list[tuple[int, int]] = []

        for interval in found_intervals:
            if not non_overlapping_intervals:
                non_overlapping_intervals.append(interval)
                continue

            last_interval = non_overlapping_intervals[-1]

            if interval[0] <= last_interval[1] and (interval[1] - interval[0]) > (
                last_interval[1] - last_interval[0]
            ):
                non_overlapping_intervals[-1] = interval
                continue

            non_overlapping_intervals.append(interval)

        matched_texts: list[str] = []
        other_texts: list[str] = []

        last_text_begin_index = 0
        for begin, end in non_overlapping_intervals:
            other = text[last_text_begin_index:begin]
            if other:
                other_texts.append(other)

            matched = text[begin:end]
            if matched:
                matched_texts.append(matched)

            last_text_begin_index = end

        other_texts.append(text[last_text_begin_index:])

        ret: list[str] = clean(matched_texts)

        chinese_chunks: list[str] = []
        english_chunks: list[str] = []
        for text in other_texts:
            chinese_chunks += clean(re.findall(r"([\u4e00-\u9fa5]+)", text))
            english_chunks += clean(re.findall(r"([^\u4e00-\u9fa5]+)", text))

        for chunk in english_chunks:
            ret += [
                i.strip()
                for i in re.findall(r"([a-zA-Z0-9]+|[^\u4e00-\u9fa5a-zA-Z0-9]+)", chunk)
                if i.strip()
            ]

        for chunk in chinese_chunks:
            ret += [
                i.strip()
                for i in list(jieba.cut(chunk, cut_all=False, HMM=True))
                if i.strip()
            ]

        ret = self.filter(ret)

        ret = list(set(ret))


        return ret

    def filter(self, texts: list[str]) -> list[str]:


        return texts

    def extract(self, text: str, enable_block_list: bool = True) -> list[Item]:
        text = beautifyText(text)

        text = text.upper()

        if enable_block_list:
            for block in self.block_list:
                text = text.replace(block, "")

        usdt_pattern = re.compile(r"(?<![A-Za-z])[uU](?![A-Za-z0-9])")
        text = usdt_pattern.sub(" USDT ", text)

        ret: list[Item] = []

        for name in self.cut(text):
            if not name in self.name_to_id:
                continue
            item = Item(key=name, meta=[])
            for id in self.name_to_id[name]:
                entity_id = self.dict[id]["id"]
                entity_type = self.dict[id]["type"]
                if any(
                    e for e in item.meta if e.id == entity_id and e.type == entity_type
                ):
                    continue
                item.meta.append(
                    Entity(
                        id=entity_id,
                        name=self.dict[id]["name"],
                        alias=self.dict[id]["alias"],
                        type=entity_type,
                        dynamic=self.dict[id]["dynamic"],
                        key=name,
                    )
                )
            ret.append(item)

        for item in ret:
            item.meta.sort(
                key=lambda x: x.dynamic["rank_id"] if "rank_id" in x.dynamic else 0
            )

        return ret


jb = JB()
