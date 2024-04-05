import decimal
import html2text
from datetime import datetime



def remove_lines(text: str) -> str:
    return text.replace("\n", " ").replace("\r", "")


def format_datetime(dt: datetime) -> str:
    return f"{dt.year}-{dt.month}-{dt.day} {dt.hour}:{dt.minute}:{dt.second}"


def html2md(html: str) -> str:
    if not html:
        return ""
    parser = html2text.HTML2Text()
    parser.ignore_links = True
    parser.ignore_images = True
    parser.ignore_emphasis = True
    parser.ignore_tables = True
    parser.ignore_images = True

    md = parser.handle(html)
    md = "\n\n".join([i.strip() for i in md.split("\n\n") if i.strip() != ""])
    md = "\n".join([i.strip() for i in md.split("\n") if i.strip() != ""])

    return md


def format_price_cn(price: float) -> str:
    if price is None:
        return ""

    # fallback
    ret = str(price)

    if price >= 100_000_000:
        ret = f"${round(price / 100_000_000, 2)}*100 million"

    elif price >= 1_000_000:
        ret = f"${round(price / 1_000_000, 1)} million"

    elif price >= 10_000:
        ret = f"${round(price / 10_000, 1)}*10 k"

    elif price >= 1:
        ret = f"${round(price, 0)}"

    elif price <= 1 and price >= 0.0001:
        ret = f"${round(price, 4)}"

    elif price < 0.0001 and price > 0:
        ctx = decimal.Context()
        ctx.prec = 20
        ret = format(ctx.create_decimal(repr(price)), "f")
        before, after = ret.split(".")
        after = after.rstrip("0")
        after = after.lstrip("0")
        zero_count = len(ret) - len(before) - len(after) - 1
        ret = "$0.{" + str(zero_count) + "}" + after[:3]

    elif price == 0:
        ret = "$0"

    return ret


def format_number_cn(num: float) -> str:
    ret = str(num)

    if num >= 100_000_000:
        ret = f"${round(num / 100_000_000)}*100 million"

    elif num >= 10_000:
        ret = f"${round(num / 10_000)} million"

    elif num >= 100:
        ret = f"${round(num)}"

    elif num >= 1:
        ret = f"${round(num, 2)}"

    return ret


def format_change_percent(num: float) -> str:
    ret = str(num)

    sign = ""
    if num > 0:
        sign = "+"
    if num < 0:
        sign = ""

    if abs(num) >= 10_000:
        ret = f"{round(num / 100)}X"
    elif abs(num) >= 100:
        ret = f"{round(num)}%"
    elif abs(num) >= 0.0001:
        ret = f"{round(num, 1)}%"

    return sign + ret


def timestamp_to_datetime_str(ts: int):
    unlock_time_datetime = datetime.fromtimestamp(ts)
    return unlock_time_datetime.strftime("%Y-%m-%d %H:%M:%S")
