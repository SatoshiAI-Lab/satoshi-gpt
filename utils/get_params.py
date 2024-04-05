import datetime
from models import Context


def is_number(string):
    try:
        int(string)
        return True
    except ValueError:
        return False


def get_route_map_params(question: str) -> list:
    default_params = [7, "pass", "day"]

    variable_time_keys = {
        "过去": [2, "pass"],
        "这": [1, "pass"],
        "近": [1, "pass"],
        "前": [1, "pass"],
        "接下来": [3, "future"],
        "后": [1, "future"],
        "未来": [2, "future"],
    }

    time_keys = {
        "前": [2, "pass"],
        "昨": [1, "pass"],
        "刚刚": [1, "this"],
        "刚才": [1, "this"],
        "今": [1, "this"],
        "明": [1, "future"],
        "后": [2, "future"],
        "上周": [1, "pass"],
        "上个": [1, "pass"],
        "上一": [1, "pass"],
        "上1": [1, "pass"],
        "本": [1, "this"],
        "这": [1, "this"],
        "下": [1, "future"],
    }
    unit_keys = {
        "天": "day",
        "日": "day",
        "早": "day",
        "晨": "day",
        "晚": "day",
        "刚刚": "day",
        "刚才": "day",
        "周": "week",
        "星期": "week",
        "礼拜": "week",
        "月": "month",
    }
    cn_num = {
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }

    is_variable = False
    for key, val in variable_time_keys.items():
        if key in question:
            total_count = 0
            key_index = question.find(key)
            count = question[key_index + val[0]]

            if not is_number(count) and not count in cn_num:
                default_params[1] = val[1]
                continue

            if count in cn_num:
                total_count = cn_num[count]
            else:
                count2 = question[key_index + val[0] + 1]
                if is_number(count2):
                    total_count = int(count) + int(count2) 
                else:
                    total_count = count

            default_params[0] = total_count
            default_params[1] = val[1]
            is_variable = True

    if not is_variable:
        for key, val in time_keys.items():
            if key in question:
                default_params[0] = val[0]
                default_params[1] = val[1]

    for key, val in unit_keys.items():
        if key in question:
            default_params[2] = val

    res_params = [default_params[0], default_params[1], "day"]

    if default_params[2] == "week":
        res_params[0] = default_params[0] * 7

        if default_params[1] == "this":
            weekday = datetime.datetime.today().weekday()
            week_left = 6 - weekday
            pass_week = weekday

            res_params[0] = pass_week
            res_params.append(week_left)

    if default_params[2] == "month":
        res_params[0] = default_params[0] * 30


    return res_params

