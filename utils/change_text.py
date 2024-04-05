import re
from numpy import delete
from models import Context, Reference

def extract_first_number(string):
    pattern = r"\d+"  
    match = re.search(pattern, string)
    if match:
        return match.group()
    else:
        return "7"  

def remove_emojis(text: str) -> str:
    after_filte_emoji = remove_between(text)
    res = remove_star(after_filte_emoji)

    return res

def remove_between(text: str) -> str:
    pattern = r"https?://\S+"
    cleaned_text = re.sub(pattern, "", text)
    return cleaned_text

def remove_star(text: str) -> str:
    text = text.replace("#", "")
    return text

def extract_numbers_within_brackets(string):
    pattern = r"\[(\d+)\]"  
    matches = re.findall(pattern, string)
    return matches

def remove_same_content(ctx: Context, total_data_list: list[Reference]):
    res = extract_numbers_within_brackets(ctx.live_content)
    num_list = list(set(res))

    total_data_list_res: list[Reference] = []

    for i in total_data_list:
        is_same = False
        for num in num_list:
            if num in ctx.add_references:
                add_ref_cont = ctx.add_references[num]["content"]
                if i.content == add_ref_cont:
                    is_same = True
                    break
        if not is_same:
            total_data_list_res.append(i)

    return total_data_list_res
