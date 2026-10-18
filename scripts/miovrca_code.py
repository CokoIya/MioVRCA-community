# SPDX-License-Identifier: GPL-3.0-only OR PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 天川澪 (Coko_Iya). Part of MioVRCA: https://github.com/CokoIya/MioVRC_AssetManager (terms in LICENSE.md)
"""MioVRCA 的分享码：方案（MIOVRCA-RECIPE-1:）、实测数据（MIOVRCA-FIT-1:）、创作者名片（MIOVRCA-PROFILE-1:）和
作品（MIOVRCA-WORK-1:）。

分享码 = 前缀 + base64url(CRC32(内容，4 字节大端) + raw deflate(内容，预设字典))。
字典和 MioVRCA 程序里的一样（internal/ai/share.go、fits.go，internal/socialapi/codes.go），属于这个版本的分享码，
不能改动。
"""
import base64
import binascii
import re
import zlib

RECIPE_PREFIX = "MIOVRCA-RECIPE-1:"
FIT_PREFIX = "MIOVRCA-FIT-1:"
PROFILE_PREFIX = "MIOVRCA-PROFILE-1:"
WORK_PREFIX = "MIOVRCA-WORK-1:"
MAX = 512 * 1024  # 内容最大的字节数

RECIPE_DICT = (
    "\"materials\":[{\"object\":\"\",\"slot\":0,\"material\":\"Assets/.mat\"}]\"kind\":\"toggle\",\"kind\":\"part\",\"kind\":\"s"
    "trip\",\"kind\":\"skin\",\"kind\":\"install\",\"头发\",\"配饰\",\"道具\",\"皮肤\",\"表情\",\"光影\",\"互动\",\"面捕\",\"素体\",\"其他\",\"materialsFro"
    "m\":\"Assets/\",\"default\":true,\"show\":true,{\"format\":\"miovrca-recipe\",\"schema\":1,\"name\":\"\",\"note\":\"\",\"c"
    "reated\":17,\"app\":\"1.8.0\",\"plugin\":\"1.5.4\",\"base\":{\"prefab\":\"Assets/\",\"name\":\"\"},\"hierarchy\":\"\",\"asse"
    "ts\":[{\"key\":\"booth:\",\"name\":\"\",\"boothId\":\"\",\"url\":\"https://booth.pm/ja/items/\",\"prefab\":\"Assets/\",\"k"
    "ind\":\"衣服\",\"version\":\"\",\"object\":\"\",\"place\":true,\"active\":true}],\"menus\":[{\"root\":\"\",\"parameter\":\"\",\""
    "items\":[{\"kind\":\"outfit\",\"path\":[\"衣服\"],\"label\":\"\",\"objects\":[\"\"]},{\"kind\":\"outfit\",\"path\":[\"衣服\"],\"la"
    "bel\":\"\",\"objects\":[\"\"]}]}]}"
).encode("utf-8")

FIT_DICT = (
    "\"shapes\":[\"Shrink_Chest\",\"Shrink_Waist\",\"Shrink_Leg\",\"Shrink_Arm\",\"Shrink_Hip\"],\"cutter\":true,\"hint\""
    ":\"community\",\"hint\":\"author\",\"hint\":\"local\",{\"format\":\"miovrca-fits\",\"schema\":1,\"app\":\"1.8.0\",\"recor"
    "ds\":[{\"at\":17,\"base\":\"\",\"asset\":{\"name\":\"\",\"boothId\":\"\",\"kind\":\"衣服\"},\"prefab\":\"\",\"clip\":0,\"after\":0,"
    "\"ok\":true},{\"at\":17,\"base\":\"\",\"asset\":{\"name\":\"\",\"boothId\":\"\",\"kind\":\"衣服\"},\"prefab\":\"\",\"clip\":0,\"aft"
    "er\":0,\"ok\":true}]}"
).encode("utf-8")


PROFILE_DICT = (
    '"label":"","following":["",""],"birthday":{"month":1,"day":1},"bases":["Manuka","Kikyo","Karin","Shinano","Mamehinata","Rusk","Chiffon","Lime","Airi","Sio","Moe"],'
    '{"kind":"website","url":"https://"},{"kind":"github","url":"https://github.com/"},{"kind":"qq_group","url":"https://qm.qq.com/q/"},{"kind":"discord","url":"https://discord.gg/"},'
    '{"kind":"douyin","url":"https://www.douyin.com/user/"},{"kind":"xiaohongshu","url":"https://www.xiaohongshu.com/user/profile/"},{"kind":"pixiv","url":"https://www.pixiv.net/users/"},'
    '{"kind":"youtube","url":"https://www.youtube.com/@"},{"kind":"bilibili","url":"https://space.bilibili.com/"},{"kind":"jinxxy","url":"https://jinxxy.com/"},{"kind":"gumroad","url":"https://.gumroad.com/"},'
    '{"kind":"xianyu","url":"https://www.goofish.com/"},{"kind":"x","url":"https://x.com/"},{"kind":"booth_shop","url":"https://.booth.pm/"}],'
    '"avatar":"/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAA'
    '{"nickname":"","bio":"","langs":["zh","ja","en"],"vrchat":"https://vrchat.com/home/user/usr_","links":['
).encode("utf-8")

WORK_DICT = (
    '"replace":"w","rights_ok":true,'
    '{"kind":"website","url":"https://"},{"kind":"pixiv","url":"https://www.pixiv.net/artworks/"},{"kind":"x","url":"https://x.com/"},{"kind":"youtube","url":"https://www.youtube.com/@"},{"kind":"bilibili","url":"https://space.bilibili.com/"},'
    '{"kind":"jinxxy","url":"https://jinxxy.com/"},{"kind":"gumroad","url":"https://.gumroad.com/l/"},{"kind":"netdisk","url":"https://pan.baidu.com/s/","label":"提取码"},{"kind":"xianyu","url":"https://www.goofish.com/item?id="},'
    '{"kind":"booth_item","url":"https://booth.pm/ja/items/"},{"kind":"booth_shop","url":"https://.booth.pm/"}],'
    '"recipe":"MIOVRCA-RECIPE-1:","cover":"/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAA'
    '"video":"https://www.youtube.com/watch?v=","video":"https://youtu.be/","video":"https://x.com//status/","video":"https://www.bilibili.com/video/BV",'
    '{"name":"","url":"https://booth.pm/ja/items/","shop":""},{"name":"","url":"https://booth.pm/ja/items/","shop":""}],"links":['
    '{"title":"","desc":"","base":"","assets":['
).encode("utf-8")

KINDS = {"recipe": ("RECIPE", RECIPE_PREFIX, RECIPE_DICT), "fit": ("FIT", FIT_PREFIX, FIT_DICT),
         "profile": ("PROFILE", PROFILE_PREFIX, PROFILE_DICT), "work": ("WORK", WORK_PREFIX, WORK_DICT)}

class CodeError(ValueError):
    pass


def _letters(text, at):
    """分享码的字母，跨过聊天软件加的空格和换行。返回按空白分开的几段。"""
    pieces, cur = [], []
    for c in text[at:]:
        if c.isascii() and (c.isalnum() or c in "-_"):
            cur.append(c)
        elif c == "+":
            cur.append("-")
        elif c == "/":
            cur.append("_")
        elif c in " \r\n\t\u00a0\u3000\u200b":
            if cur:
                pieces.append("".join(cur))
                cur = []
        else:
            break
    if cur:
        pieces.append("".join(cur))
    return pieces[:40]


def _decode(body, zdict):
    try:
        raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
    except (binascii.Error, ValueError):
        raise CodeError("分享码有误")
    if len(raw) < 6:
        raise CodeError("分享码有误")
    want = int.from_bytes(raw[:4], "big")
    d = zlib.decompressobj(wbits=-15, zdict=zdict)
    try:
        data = d.decompress(raw[4:], MAX + 1)
    except zlib.error:
        raise CodeError("分享码有误")
    if len(data) > MAX or d.unconsumed_tail:
        raise CodeError("分享码中的内容过大")
    if not d.eof:
        raise CodeError("分享码有误")
    if binascii.crc32(data) & 0xFFFFFFFF != want:
        raise CodeError("分享码有误")
    return data


def find(text, kind):
    """在一段文字（议题正文、聊天记录）里找到分享码并解开，返回内容（bytes）。kind: recipe、fit、profile 或 work。"""
    name, _, zdict = KINDS[kind]
    m = re.search(r"MIOVRCA-" + name + r"-([0-9]{1,3})[\t\n\f\r ]*[:：]", text, re.I | re.A)
    if not m:
        raise CodeError("没有找到分享码")
    if int(m.group(1)) != 1:
        if int(m.group(1)) > 1:
            raise CodeError("该分享码由更新版本的 MioVRCA 生成（第 %d 版），请更新本仓库的脚本" % int(m.group(1)))
        raise CodeError("分享码不完整或有误")
    pieces = _letters(text, m.end())
    err = CodeError("分享码不完整或有误")
    for k in range(len(pieces), 0, -1):  # 后面的聊天文字也可能是字母：从全部到第一段逐个试，CRC 说明哪个是
        try:
            return _decode("".join(pieces[:k]), zdict)
        except CodeError as e:
            if str(e) != "分享码有误":
                err = e
    raise err


def encode(data, kind):
    """把内容做成分享码（测试和手工处理用）。"""
    _, prefix, zdict = KINDS[kind]
    c = zlib.compressobj(9, zlib.DEFLATED, -15, zdict=zdict)
    body = (binascii.crc32(data) & 0xFFFFFFFF).to_bytes(4, "big") + c.compress(data) + c.flush()
    return prefix + base64.urlsafe_b64encode(body).decode().rstrip("=")
