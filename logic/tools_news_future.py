from ai.GPT import gpt_gen_template_stream
from ai.reference import add_references, clear_references
from datasource.active_infos import get_active_infos_by_condition
from models import Define_source, Reference, ResponseChunk, Context, Entity

async def get_future_data(
    ctx: Context, single_entity: Entity, recent_days: int
) -> list[Reference]:
    day_lastest_news = await get_active_infos_by_condition(
        ctx,
        entity_id=single_entity.id,
        pass_future="future",
        day=999,
        include_sort=[
            Define_source(type="news"),
            Define_source(type="route_map"),
            Define_source(type="twitter"),
        ],
    )
    def compare_published_at(item):
        return item.published_at

    day_lastest_news.sort(key=compare_published_at)

    return day_lastest_news


async def get_future_main(ctx: Context, single_entity: Entity):
    recent_days = 22

    lang_dict = {
        "zh": "暂无未来规划相关动态\n\n",
        "en": "There is no news related to future plans.\n\n",
    }

    total_data_list = await get_future_data(ctx, single_entity, recent_days)

    if not total_data_list:
        yield ResponseChunk(
            answer_type="news_stream",
            text=lang_dict[ctx.global_.language],
            hyper_text="",
            meta={},
        )
        return

    yield add_references(total_data_list)

    async for i in await gpt_gen_template_stream(
        ctx=ctx,
        template="future_plan_v2",
        answer_type="news_stream",
        total_data_list=total_data_list,
        single_entity=single_entity,
    ):
        yield i

    yield clear_references()

    yield ResponseChunk(answer_type="news_stream", text="\n\n")
