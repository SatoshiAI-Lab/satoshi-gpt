from datetime import datetime
import json
import re
from fastapi import background
import html2text
from pydantic import BaseModel, Field, field_serializer
from typing import Union, Literal, TypeAlias, Any


class EntityExtractRequestForNews(BaseModel):
    title: str


ENTITYTYPE2ID = {
    "coin": 1,
    "label": 2,
    "software": 3,
    "people": 4,
    "economy": 5,
}
ENTITYTYPE2ID_EN = {
    "coin": 1,
    "label": 2,
    "software": 3,
    "people": 4,
    "economy": 5,
}
ENTITYID2TYPE = {v: k for k, v in ENTITYTYPE2ID.items()}
ENTITYID2TYPE_EN = {v: k for k, v in ENTITYTYPE2ID_EN.items()}

NOENTITYTYPE2ID = {
    "coin": 8,
    "label": 9,
    "software": 10,
}


class No_entity(BaseModel):
    classify_type: int = 8
    question: str = ""


class Reference(BaseModel):
    id: int | None = None
    type: Literal["twitter", "news", "announcement", "route_map"]
    content: str
    published_at: datetime  
    title: str = ""
    url: str = ""
    datetime_str: datetime | str | None = None
    sentiment: int | None = None  
    order_point: int = 0

    @field_serializer("published_at")
    def format_published_at(self, publish_at: datetime, _info):
        return publish_at.strftime("%Y-%m-%d %H:%M:%S")


class Entity(BaseModel):
    id: int
    name: str
    alias: list[str] = []
    type: int
    key: str = ""
    dynamic: dict = {}
    news: list[Reference] = []
    vector_news: list[Reference] = []


class Item(BaseModel):
    key: str
    meta: list[Entity]


class Knowledge(BaseModel):
    title: str
    content: str
    similarity: float

    def __str__(self):
        return f"### {self.title}\n{self.content}\n"

    def __repr__(self):
        return self.__str__()


class News_pg(BaseModel):
    title: str
    content: str
    published_at: str
    similarity: float

    def __str__(self):
        return f"-({self.published_at}){self.title}\n{self.content}\n"

    def __repr__(self):
        return self.__str__()


class ResponseChunk(BaseModel):
    answer_type: str
    text: str = ""
    hyper_text: str = ""
    meta: dict[Any, Any] = {}
    error: str = ""

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if self.hyper_text and not self.text:
            h2t = html2text.HTML2Text()
            h2t.ignore_emphasis = True
            h2t.ignore_images = True
            h2t.ignore_links = True
            h2t.body_width = 0
            content = h2t.handle(self.hyper_text)
            # clean 0x00
            content = content.replace("\x00", "")
            # clean links
            content = re.sub(r"\[.*?\]\(.*?\)", "", content)
            content = re.sub(r"!\[.*?\]\(.*?\)", "", content)
            # clean lines
            lines = [i.strip() for i in content.split("\n\n")]
            while "" in lines:
                lines.remove("")

            content = "\n\n".join(lines)
            content = "\n".join([i.strip() for i in content.split("\n")])
            self.text = content + "\n"

    def __str__(self):
        dic = {
            "answer_type": self.answer_type,
            "text": self.text,
            "hyper_text": self.hyper_text,
            "error": self.error,
            "meta": self.meta,
        }

        return "data: " + json.dumps(dic, ensure_ascii=False) + "\n\n"

    def __repr__(self):
        return self.text

    def encode(self, *args, **kargs):
        return self.__str__().encode(*args, **kargs)


class Context(BaseModel):
    question: str
    history: list[dict] = []

    class Global(BaseModel):
        username: str = "test"
        uuid: str = ""
        is_vip: bool = False
        user_id: int | None = None
        ip: str | None = None

        language: Literal["zh", "en"] = "zh"

        access_token:str=""

    global_: Global = Global()
    selected_entities: list[Entity] = []
    stream: bool = False
    entity_id: str = ""
    entities: list[Entity] = []
    only_token_news: list[Reference] = []
    knowledges: list[Knowledge] = []
    no_entity_news: list[Reference] = []
    no_entity_vector_news: list[Reference] = []
    route_map: list[Reference] = []
    route_map_vector: list[str] = []
    live_content: str = ""
    add_references: dict[Any, Any] = {}
    fluctuation: str = ""
    add_information_type: list[
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
        ]
    ] = []
    info_requirement: bool = False
    event_requirement: bool = False
    help_requirement: bool = False
    filter_requirement: bool = False
    short_info_requirement: bool = False
    
    intent_stream:str=""


class GPTMessage(BaseModel):
    role: Literal["system", "assistant", "user"]
    content: str


class GPTQuery(BaseModel):
    messages: list[GPTMessage]
    temperature: float = 0


class ChatForTestMessage(BaseModel):
    question: str = Field(
        title="Input your question",
        min_length=1,
        max_length=100,
    )


class ChatForTestMessage2(BaseModel):
    question: str = Field(
        title="Input your question",
        min_length=1,
        max_length=100,
    )
    prompt: str = Field(
        title="Input your prompt",
        min_length=1,
        max_length=100,
    )
    token_name: str = ""
    token_id: int



class Preference(BaseModel):
    language: str = "zh"


class ChatUserInfo(BaseModel):
    username: str
    is_vip: bool
    preference: Preference


class ChatUserQuery(BaseModel):
    user_info: ChatUserInfo
    history: list[GPTMessage]
    stream: bool = False
    question: str = Field(
        title="Input your question",
        min_length=1,
        max_length=100,
    )

    type: Union[int, None] = None
    id: Union[int, None] = None

    class UserSelectedEntity(BaseModel):
        id: int
        type: int

    selected_entities: list[UserSelectedEntity] = []


AnswerType: TypeAlias = Literal[
    "chat_stream",
    "token_basic",
    "news",
    "news_stream",
    "risk_analysis",
    "risk_analysis_stream",
    "review",
    "data_insights",
    "data_insights_stream",
    "tech_analyze",
    "tech_analyze_stream",
]


class Define_source(BaseModel):
    type: str = ""  
    limit: int = -1 


