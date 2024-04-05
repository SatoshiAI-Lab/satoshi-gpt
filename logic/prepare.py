from pydantic import BaseModel
from models.models import  Context, Entity, Item
from entity_extraction.jb import jb


class InteractiveResponse(BaseModel):
    entities: list[Entity]

    def __bool__(self):
        return bool(self.entities)


def is_in_entities(entities: list[Entity], entity: Entity) -> Entity | None:
    for e in entities:
        if e.id == entity.id and e.type == entity.type:
            return e
    return None


def user_have_selected_entity(
    selected_entities: list[Entity], item_meta: list[Entity]
) -> Entity | None:
    for e in item_meta:
        if is_in_entities(selected_entities, e):
            return e
    return None


def entity_extract(ctx: Context) -> tuple[InteractiveResponse, list[Entity]]:
    entities = []
    ret: list[Entity] = []
    extracted_items: list[Item] = jb.extract(ctx.question, enable_block_list=True)
    for item in extracted_items:
        if len(item.meta) <= 1:
            entities.extend(item.meta)
            continue

        if full_info_entity := user_have_selected_entity(
            ctx.selected_entities, item.meta
        ):
            entities.append(full_info_entity)
            continue

        for entity in item.meta:
            if is_in_entities(ret, entity):
                continue
            ret.append(entity)

    return InteractiveResponse(entities=ret), entities

