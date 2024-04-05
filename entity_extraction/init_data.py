from models import Entity
from db.postgre import postgresql


async def download_block_list() -> list[str]:
    query = """
        select name from other_entities
    """
    print("Downloading block list from database...")
    rows = await postgresql.fetch_all(query=query)
    ret: list[str] = []
    for row in rows:
        obj = row[0]
        for name in obj:
            ret.append(name.upper())

    return ret


async def download_tokens() -> list[Entity]:
    query = "SELECT id, symbol, rank_id, intro, intro_detail, use, team, rank_id, alias, name FROM token where is_block = 0"
    print("Downloading token info from database...")
    rows = await postgresql.fetch_all(query=query)

    tokens: list[Entity] = []
    for row in rows:
        info = {}
        if row[3]:
            info["intro"] = row[3]
        if row[4]:
            info["intro_detail"] = row[4]
        if row[5]:
            info["use"] = row[5]
        if row[6]:
            info["team"] = row[6]
        if type(row[7]) == int:
            info["rank_id"] = row[7]

        alias = [row[1]]
        if row[8]:
            alias += row[8]
        if row[9]:
            alias.append(row[9])
        alias = list(set(i.upper() for i in alias))

        tokens.append(
            Entity(
                id=row[0],
                name=row[1],
                alias=alias,
                dynamic=info,
                type=1,
            )
        )

    return tokens


async def download_labels() -> list[Entity]:
    ret: list[Entity] = []
    query = "SELECT id, name, alias, intro FROM label where is_deleted = 0"
    print("Downloading label info from database...")
    rows = await postgresql.fetch_all(query=query)

    for row in rows:
        info = {}
        if row[3]:
            info["intro"] = row[3]

        alias = [row[1]]
        if row[2]:
            alias += row[2]
        alias = list(set(i.upper() for i in alias))

        ret.append(
            Entity(
                id=row[0],
                name=row[1],
                alias=alias,
                dynamic=info,
                type=2,
            )
        )

    return ret


async def download_software() -> list[Entity]:
    ret: list[Entity] = []
    query = "SELECT id, name, alias, intro, long_intro, website, category, downloads, news_names FROM software"
    print("Downloading software info from database...")
    rows = await postgresql.fetch_all(query=query)

    for row in rows:
        info = {}
        if row[3]:
            info["intro"] = row[3]
        if row[4]:
            info["long_intro"] = row[4]
        if row[5]:
            info["website"] = row[5]
        if row[6]:
            info["category"] = row[6]
        if row[7]:
            info["downloads"] = row[7]
        if row[8]:
            info["news_names"] = row[8]

        alias = [row[1]]
        if row[2]:
            alias += row[2]
        alias = list(set(i.upper() for i in alias))

        ret.append(
            Entity(
                id=row[0],
                name=row[1],
                alias=alias,
                dynamic=info,
                type=3,
            )
        )

    print("Downloaded", len(ret), "software info from database")

    return ret


async def download_people() -> list[Entity]:
    ret: list[Entity] = []
    query = "SELECT id, name, alias from people"
    print("Downloading software info from database...")
    rows = await postgresql.fetch_all(query=query)

    for id, name, alias in rows:
        alias = [name] + alias if alias else [name]
        alias = list(set(i.upper() for i in alias))

        ret.append(
            Entity(
                id=id,
                name=name,
                alias=alias,
                dynamic={},
                type=4,
            )
        )

    return ret


async def download_economy() -> list[Entity]:
    ret: list[Entity] = []
    query = "SELECT id, name, alias from economy"
    print("Downloading economy info from database...")
    rows = await postgresql.fetch_all(query=query)

    for id, name, alias in rows:
        alias = [name] + alias if alias else [name]
        alias = list(set(i.upper() for i in alias))

        ret.append(
            Entity(
                id=id,
                name=name,
                alias=alias,
                dynamic={},
                type=5,
            )
        )

    return ret
