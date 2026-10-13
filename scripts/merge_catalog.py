# -*- coding: utf-8 -*-
"""合并官网商品描述与 MCP 官方营养数据，生成统一商品库。

数据来源分工：
- 卖点描述 (desc)：麦当劳官网产品页（原文，权威表述）
- 营养成分：MCP list-nutrition-foods（160 个餐品，远多于官网）

官网库只有 29 个商品且无早餐；MCP 库有 158 个餐品覆盖早餐/儿童餐/咖啡/沙拉，
但不含卖点描述。因此合并后：
- 两边都有的商品 → 描述 + 营养俱全（最佳）
- 仅 MCP 有的商品 → 营养齐全，描述留空（运行时提示"以官网为准"，不编造卖点）

名称对齐：官网与 MCP 存在规格差异（如官网"薯条"≈ MCP"中薯条"），
按关键词规则映射，对不上的不做猜测合并。

用法：
    python merge_catalog.py
输出：references/catalog.json
"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DB = os.path.join(BASE, "references", "mcd_products.json")
MCP_DB = os.path.join(BASE, "references", "mcp_nutrition.json")
OUT = os.path.join(BASE, "references", "catalog.json")

# 官网名 -> MCP 餐品名 的显式映射（只列确实对应的）
NAME_MAP = {
    "薯条": "中薯条",
    "麦乐鸡 (5块)": "麦乐鸡5块",
    "那么大鸡排（椒盐风味）": "那么大鸡排",
    "圆筒冰淇淋": "圆筒冰淇淋",
    "可口可乐": "可乐中杯",
    "无糖可口可乐": "无糖可口可乐中杯",
    "玉米杯": "小杯玉米杯",
}

# MCP 餐品 -> 分类（关键词优先，顺序即优先级，务必先判汉堡再判鸡翅等）
CATEGORY_RULES = [
    # 儿童餐 / 早餐需最先判定，否则会被通用规则抢走
    ("果然多肉", "儿童餐"), ("牛气满满", "儿童餐"), ("苹板", "儿童餐"),
    ("专薯鱼", "儿童餐"), ("绝代双翅", "儿童餐"), ("蜜汁快乐", "儿童餐"),
    ("儿童鱼排堡", "儿童餐"), ("薯鱼", "儿童餐"),
    ("麦满分", "早餐"), ("炒双蛋堡", "早餐"), ("早安营养卷", "早餐"),
    ("鸡肉粥", "早餐"), ("脆香油条", "早餐"), ("脆薯饼", "早餐"),
    ("猪柳", "早餐"), ("烟肉蛋", "早餐"), ("火腿扒麦满分", "早餐"),
    # 汉堡：必须在"鸡翅/鸡腿"之前，否则麦香鸡/麦香鱼会被误判
    ("巨无霸", "汉堡"), ("牛堡", "汉堡"), ("鸡堡", "汉堡"), ("鱼堡", "汉堡"),
    ("堡", "汉堡"),
    ("麦香鸡", "汉堡"), ("麦香鱼", "汉堡"),   # 名称无"堡"字，需显式列出
    ("奶冻", "甜品"), ("新地", "甜品"), ("麦旋风", "甜品"), ("派", "甜品"),
    ("冰淇淋", "甜品"), ("雪冰", "甜品"), ("拉明顿", "甜品"), ("麦旋酷", "甜品"),
    ("沙拉", "沙拉"),
    # 小食
    ("V翅", "小食"), ("鸡翅", "小食"), ("麦乐鸡", "小食"), ("薯条", "小食"),
    ("鸡球", "小食"), ("鸡排", "小食"), ("香肠", "小食"), ("脆汁鸡", "小食"),
    ("玉米杯", "小食"), ("苹果片", "小食"), ("薯饼", "小食"), ("趣鸡球", "小食"),
    ("多笋卷", "小食"), ("卷", "小食"),
    # 饮品
    ("咖啡", "饮品"), ("美式", "饮品"), ("拿铁", "饮品"), ("阿芙佳朵", "饮品"),
    ("红茶", "饮品"), ("绿茶", "饮品"), ("奶茶", "饮品"), ("牛奶", "饮品"),
    ("奶铁", "饮品"), ("燕麦", "饮品"), ("豆浆", "饮品"), ("果汁", "饮品"),
    ("可乐", "饮品"), ("雪碧", "饮品"), ("怡泉", "饮品"), ("柠檬", "饮品"),
    ("气泡", "饮品"), ("朱古力", "饮品"), ("黑巧", "饮品"), ("抹茶", "饮品"),
    ("纯悦", "饮品"), ("美汁源", "饮品"), ("玛奇朵", "饮品"), ("卡布奇诺", "饮品"),
    # 兜底：儿童小食系列（命名特殊，无法靠通用关键词判定）
    ("yeyeyeye", "甜品"),
]

# 热门加权（沿用原有集合，名称对齐 MCP 口径）
HOT_NAMES = {
    "巨无霸", "麦辣鸡腿汉堡", "板烧鸡腿堡", "麦香鸡", "双层吉士汉堡",
    "麦辣鸡翅-2块", "中薯条", "麦乐鸡5块", "那么大鸡排", "薄皮焦香V翅",
    "圆筒冰淇淋", "奥利奥麦旋风", "朱古力新地", "可乐中杯", "无糖可口可乐中杯",
}


def categorize(name):
    for kw, cat in CATEGORY_RULES:
        if kw in name:
            return cat
    return "其他"


def main():
    web = json.load(open(WEB_DB, encoding="utf-8"))
    mcp_raw = json.load(open(MCP_DB, encoding="utf-8"))
    mcp = {i["productName"]: i for i in mcp_raw["items"] if i.get("productName")}

    merged = {}

    # 1) 先落 MCP 数据（含营养）
    for name, item in mcp.items():
        merged[name] = {
            "name": name,
            "category": categorize(name),
            "desc": "",                       # MCP 不提供卖点，运行时不得编造
            "nutrition": {
                "能量": f"{item['energyKj']}千焦",
                "能量kcal": f"{item['energyKcal']}千卡",
                "蛋白质": f"{item['protein']}克",
                "脂肪": f"{item['fat']}克",
                "碳水化合物": f"{item['carbohydrate']}克",
                "钠": f"{item['sodium']}毫克",
                "钙": f"{item['calcium']}毫克",
            },
            "source": "mcp",
            "desc_url": "",
            "hot": name in HOT_NAMES,
        }

    # 2) 用官网数据补描述与链接
    for _, w in web.items():
        target = NAME_MAP.get(w["name"])
        # 名称完全一致或映射命中时才合并，避免规格错配
        key = target if target in merged else (w["name"] if w["name"] in merged else None)
        if key:
            merged[key]["desc"] = w["desc"]
            merged[key]["desc_url"] = w["url"]
            merged[key]["source"] = "mcp+web"

    with_desc = sum(1 for v in merged.values() if v["desc"])
    result = {
        "note": "营养数据来自 MCP list-nutrition-foods；卖点描述来自官网原文，"
                "无描述的商品运行时不得编造卖点。",
        "counts": {
            "total": len(merged),
            "with_desc": with_desc,
            "mcp_only": sum(1 for v in merged.values() if v["source"] == "mcp"),
        },
        "items": list(merged.values()),
    }
    json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"合并完成：共 {len(merged)} 项，其中有官网描述 {with_desc} 项，"
          f"仅MCP {result['counts']['mcp_only']} 项")
    by_cat = {}
    for v in merged.values():
        by_cat.setdefault(v["category"], []).append(v["name"])
    for cat in sorted(by_cat):
        print(f"  {cat}: {len(by_cat[cat])}")


if __name__ == "__main__":
    main()