import os
import re


def is_Chinese(word):
    for ch in word:
        if "\u4e00" <= ch <= "\u9fff":
            return True
    return False


def is_al_num(word):
    word = word.replace("_", "").replace(" ", "").replace("()", "").encode("UTF-8")
    if word.isalpha():
        return True
    if word.isdigit():
        return True
    if word.isalnum():
        return True
    return False


def beautifyText(text, pattern=r"([\u4e00-\u9fff])", isloop=True):
    res = re.compile(pattern) 

    p1 = res.split(text)
    result = ""
    for index in range(len(p1)):
        str = p1[index]
        if "\n" == str:
            result += str
            continue
        if is_Chinese(str):
            result += str
        elif is_al_num(str):
            if isloop and index == 0:
                result += str.strip() + " "
            else:
                result += " " + str.strip() + " "
        else:
            if isloop:
                result += beautifyText(str, pattern=r"([。，？！,!]+)", isloop=False)
            else:
                result += str
    return result


def beatifyFile(file):
    f1 = open(file, "r+")
    infos = f1.readlines()
    print("len: " + str(len(infos)))
    f1.seek(0, 0)
    for line in infos:
        new_str = beautifyText(line, pattern=r"([\u4e00-\u9fff])", isloop=True)
        line = line.replace(line, new_str)
        f1.write(line)
    f1.close()


def test(s):
    print("origin：" + s)
    text = beautifyText(s, pattern=r"([\u4e00-\u9fff])", isloop=True)
    print("transfer：" + text)


def DirAll(pathName):
    if os.path.exists(pathName):
        fileList = os.listdir(pathName)
        for f in fileList:
            f = os.path.join(pathName, f)
            if os.path.isdir(f):
                DirAll(f)
            else:
                baseName = os.path.basename(f)
                if baseName.startswith("."):
                    continue
                print(f)
                beatifyFile(f)
