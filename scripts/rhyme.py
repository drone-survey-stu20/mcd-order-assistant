# -*- coding: utf-8 -*-
"""套餐顺口溜生成器：为随机套餐生成押韵、有节奏的评价。

设计原则：
1. 每句尽量押韵（按档位选韵脚），读起来有节奏
2. 商品名嵌入句中，用商品名本身的特征词造句，不生硬
3. 不夸大功效、不编造价格，只描述口感与体验
"""

# 场景标签 -> 该场景的开场白（按热量档位选）
# 合规要求：赛事规则禁止宣扬不健康饮食与奢靡浪费，故避免"放纵""别管热量"等表述
OPENERS = {
    "high": ["今天想吃顿好的", "来份扎实的", "好好吃一顿"],
    "mid": ["今天这顿刚刚好", "日常标配别想多", "稳稳的幸福"],
    "low": ["轻装上路这顿", "清爽在线不长肉", "给肚子减个负"],
}

# 结尾押韵句（按档位，韵脚统一）
CLOSERS = {
    "high": ["吃完就有满足感", "这一顿吃值了", "吃得满足，也算数一顿"],
    "mid": ["吃完刚刚好，不撑不饿", "这一顿拿捏得挺稳", "日常能吃就挺好"],
    "low": ["清爽无负担，晚上不闹", "吃完轻盈还能跑", "轻负担也是好伙食"],
}

# 主餐句式：{name}=商品名
MAIN_TEMPLATES = [
    "{name}打底，肉香撑满一天",
    "先来{ name}，招牌镇得住场",
    "{name}扛主旗，扛饿有底气",
    "主角{ name}，咬一口就懂了",
    "{name}上场，稳稳拿捏住",
    "肉饼管够，这顿就稳了",
    "主角一上场，别的都靠边站",
]

# 小食句式
SIDE_TEMPLATES = [
    "{name}配着吃，脆得掉渣",
    "再来点{ name}，这口酥得值",
    "{name}加入，快乐翻倍",
    "{name}垫一口，越吃越有",
    "配上{ name}，香得不行",
    "来点小食，酥脆不能少",
    "配角也不将就，这口够味",
]

# 甜品句式
DESSERT_TEMPLATES = [
    "{name}收尾，甜到心里去",
    "最后{ name}，画个甜句号",
    "{name}上桌，治愈一下",
    "餐后{ name}，幸福感满格",
    "甜点收官，这一口值了",
    "来个甜品，坏心情退散",
]

# 饮品句式
DRINK_TEMPLATES = [
    "{name}一灌，顺畅又解腻",
    "配{ name}，干饭更带劲",
    "{name}打底，舒服又清爽",
    "来口{ name}，舒坦又解压",
    "饮料跟上，清爽收个尾",
]

# 按商品特征给的针对性小句（提升真实感，非编造卖点，只描述口感）
FEATURE_HINTS = {
    "巨无霸": "双层牛肉饼，分量实在",
    "麦辣鸡腿汉堡": "微辣带劲，风味到位",
    "板烧鸡腿堡": "鸡排现烤，不腻",
    "双层吉士汉堡": "芝士拉丝，咸香刚好",
    "麦香鸡": "酥脆外衣，鸡肉嫩",
    "麦香鱼": "鳕鱼排，鲜嫩没得说",
    "汉堡包": "经典原味，简单纯粹",
    "薯条": "现炸薯条，脆得刚好",
    "麦乐鸡 (5块)": "五块入腹，蘸酱更香",
    "麦辣鸡翅": "辣翅三只，越吃越上头",
    "那么大鸡排（椒盐风味）": "厚切鸡排，椒盐带劲",
    "薄皮焦香V翅": "薄皮炸得脆，油感不腻",
    "圆筒冰淇淋": "甜筒一握，孩子最爱",
    "奥利奥麦旋风": "黑白混合，绵密带脆",
    "朱古力新地": "巧克力浓稠化不开",
    "草莓新地": "草莓酱酸甜平衡",
    "草莓麦旋风": "草莓遇上旋，甜得清新",
    "香芋派": "软心脆皮，两层口感",
    "菠萝派": "菠萝香气，热带感足",
    "玉米杯": "玉米粒粒爆汁",
    "苹果片": "红富士脆爽，解腻小能手",
    "可口可乐": "气泡一开，爽到冒泡",
    "无糖可口可乐": "零卡配方，甜味也清",
    "芝士安格斯厚牛堡": "厚牛堡大块肉，芝士拉满",
    "培根安格斯厚牛堡": "培根加厚牛，肉感爆棚",
    "不素之霸双层牛堡": "德式香肠+双层牛，狠角色",
    "培根蔬萃双层牛堡": "培根加生菜，咸香不腻",
    "双层深海鳕鱼堡": "双份鳕鱼，海味足",
}


def _pick(rng, seq, used, avoid_repeat=True):
    """从候选中取值，尽量不重复（用于同一段内避免句式雷同）。"""
    if not avoid_repeat or not used:
        v = rng.choice(seq)
        used.append(v)
        return v
    avail = [s for s in seq if s not in used]
    v = rng.choice(avail or seq)
    used.append(v)
    return v


def _fill(tpl, name):
    """填充商品名，顺手清掉模板里为对齐多写的空格。"""
    return tpl.replace("{ name}", name).replace("{name}", name)


def _overlaps(line, hint):
    """粗判两句是否语义重复：共享足够多的双字词即视为重复。"""
    def bigrams(s):
        return {s[i:i + 2] for i in range(len(s) - 1)}
    common = bigrams(line) & bigrams(hint)
    return len(common) >= 2


def build_rhyme(items, level, rng):
    """为套餐生成顺口溜评价。

    返回顺口溜多行文本。每句尽量押韵，商品名只出现一次。
    """
    by_cat = {p["category"]: p["name"] for p in items}
    used = {"汉堡": [], "小食": [], "甜品": [], "饮品": []}

    lines = [_pick(rng, OPENERS[level], [])]

    for cat in ("汉堡", "小食", "甜品", "饮品"):
        name = by_cat.get(cat)
        if not name:
            continue
        tpls = {"汉堡": MAIN_TEMPLATES, "小食": SIDE_TEMPLATES,
                "甜品": DESSERT_TEMPLATES, "饮品": DRINK_TEMPLATES}[cat]

        # 该商品有专属特征小句时，正句用不带名句式，把名额让给特征句
        hint = FEATURE_HINTS.get(name)
        pool = tpls
        if hint:
            pool = [t for t in tpls if "{ name}" in t or "{name}" in t]

        lines.append(_fill(_pick(rng, pool, used[cat]), name))
        if hint and not _overlaps(lines[-1], hint):
            lines.append(f"　└ {hint}")

    lines.append(_pick(rng, CLOSERS[level], []))
    return "\n".join(lines)