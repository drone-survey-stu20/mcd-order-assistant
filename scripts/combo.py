# -*- coding: utf-8 -*-
"""随机混搭麦当劳热门套餐，并给出逐项优点与整体评价。

用法:
    python combo.py random
    python combo.py random --count 3
    python combo.py random --no-dessert
    python combo.py --list            # 列出商品库
"""
import argparse
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rhyme as rhyme_mod

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "references", "mcd_products.json")

# 经典高热度商品，作为随机时的加权种子
HOT = {
    "巨无霸", "麦辣鸡腿汉堡", "板烧鸡腿堡", "麦香鸡", "双层吉士汉堡",
    "麦乐鸡 (5块)", "薯条", "麦辣鸡翅", "那么大鸡排（椒盐风味）",
    "圆筒冰淇淋", "奥利奥麦旋风", "朱古力新地", "可口可乐", "无糖可口可乐",
}

NAME_SETS = {
    # 热量档位 -> (套餐名候选, 一句话定位)
    "high": (["经典能量套餐", "扎实饱腹组合", "大口满足套餐",
              "高能补给套餐"],
             "分量扎实，扛饿，适合体力消耗大的日子"),
    "mid": (["元气开心套餐", "经典人气组合", "午后满足套餐", "全家欢分享套餐"],
            "热量适中，正常吃一顿刚刚好"),
    "low": (["清爽轻盈套餐", "轻负担低卡组合", "清爽解腻套餐", "轻盈果蔬搭配"],
            "热量控制得不错，吃完不困"),
}


def combo_name(rng, level):
    return rng.choice(NAME_SETS[level][0])


def load_db():
    with open(DB_PATH, encoding="utf-8") as f:
        return json.load(f)


def parse_energy(nutrition):
    """从 '2146千焦' 解析出整数千焦，用于营养汇总。"""
    m = re.match(r"([\d.]+)", nutrition.get("能量") or "")
    return float(m.group(1)) if m else 0.0


def parse_gram(nutrition, key):
    m = re.match(r"([\d.]+)", nutrition.get(key) or "")
    return float(m.group(1)) if m else 0.0


def weighted_sample(items, rng):
    """热门商品权重更高：热门权重 3，普通权重 1。"""
    weights = [3 if it["name"] in HOT else 1 for it in items]
    return rng.choices(items, weights=weights, k=1)[0]


def pick(items, rng):
    """从候选中加权随机取一个；候选为空返回 None。"""
    return weighted_sample(items, rng) if items else None


def score_desc(p, limit=70):
    """截取官网描述中较有信息量的一段作为优点摘要，尽量在句末断开。"""
    d = re.sub(r"\s+", "", p["desc"])
    # 描述本身就短（<=limit）时直接全文引用，不做截断
    if len(d) <= limit:
        return d
    for sep in ("。", "！"):
        idx = d.find(sep)
        # 断句点太靠前（少于12 字）会丢掉卖点，往后找下一个断点
        if 12 <= idx <= limit:
            return d[: idx + 1]
    # 找不到合适句末：在上限内找一个逗号收尾
    idx = d.rfind("，", 0, limit)
    if idx >= 14:
        return d[:idx] + "。"
    return d[:limit] + "…"


def build_combo(db, rng, want_dessert=True, used_mains=None):
    """组合一套套餐：主餐 + 小食 + 甜品 + 饮品。

    used_mains 为已用过的主餐名集合，用于同一次生成多套套餐时避免重复。
    """
    by_cat = {}
    for p in db.values():
        by_cat.setdefault(p["category"], []).append(p)

    burgers = by_cat.get("汉堡", []) or by_cat.get("早餐", [])
    if used_mains:
        remaining = [b for b in burgers if b["name"] not in used_mains]
        if remaining:
            burgers = remaining

    main = pick(burgers, rng)
    if main is None:
        main = pick([v for v in db.values() if v["name"] in HOT], rng)

    side = pick(by_cat.get("小食", []), rng)
    drink = pick(by_cat.get("饮品", []), rng)
    dessert = pick(by_cat.get("甜品", []), rng) if want_dessert else None

    return [i for i in [main, side, dessert, drink] if i]


def total_kj(items):
    return sum(parse_energy(i["nutrition"]) for i in items)


def review(items):
    """生成整体搭配评价，返回 (级别, 汇总句, 分项评述)。"""
    kj = total_kj(items)
    total_p = sum(parse_gram(i["nutrition"], "蛋白质") for i in items)
    cats = {i["category"] for i in items}

    if kj > 3400:
        level = "high"
    elif kj > 2100:
        level = "mid"
    else:
        level = "low"

    lines = []
    if "汉堡" in cats:
        lines.append("主餐是硬菜，蛋白质撑得住，扛饿。")
    if "小食" in cats:
        lines.append("小食负责酥脆口感和碳水，情绪价值拉满。")
    if "甜品" in cats:
        lines.append("甜品收尾，麦当劳的甜品一向稳。")
    if "饮品" in cats:
        lines.append("饮品解腻，整套吃下来不会太干。")

    summary = (f"合计约 {kj:.0f} 千焦、蛋白质 {total_p:.0f} 克。"
               f"{NAME_SETS[level][1]}。")
    return level, summary, "".join(lines)


def render(items, rng, idx=None, name=None, level=None, summary=None, detail=None,
           overflow=False, max_kj=None):
    if level is None:
        level, summary, detail = review(items)
    name = name or combo_name(rng, level)
    title = "随机套餐" if idx is None else f"随机套餐 {idx}"
    out = ["\n" + "=" * 46 + f"\n🎲 {title} · {name}\n" + "=" * 46]

    for p in items:
        n = p["nutrition"]
        out.append(f"\n【{p['category']}】{p['name']}")
        out.append(f"  优点：{score_desc(p)}")
        out.append(f"  营养：能量 {n['能量']}｜蛋白质 {n['蛋白质']}｜脂肪 {n['脂肪']}｜钠 {n['钠']}")
        out.append(f"  官网：{p['url']}")

    out.append("\n" + "-" * 46 + f"\n【整体评价】{summary}")
    if detail:
        out.append(detail)

    # 顺口溜评价（每套套餐必备）
    out.append("\n" + "-" * 46 + "\n【顺口溜评价】")
    out.append(rhyme_mod.build_rhyme(items, level, rng))

    if overflow:
        out.append(f"\n⚠️ 已尽力收敛，但暂无能量低于 {max_kj} 千焦的完整组合，"
                   f"这套超出上限，可去掉甜品或小食再试。")
    out.append("\n商品优点均引自麦当劳官网原文。要这套吗？")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["random", "list"], help="random=随机套餐 list=商品列表")
    ap.add_argument("--count", type=int, default=1, help="生成套餐数量")
    ap.add_argument("--no-dessert", action="store_true", help="不带甜品")
    ap.add_argument("--seed", type=int, default=None, help="随机种子（便于复现）")
    ap.add_argument("--json", action="store_true", help="输出 JSON，便于程序化处理")
    ap.add_argument("--max-kj", type=int, default=None,
                    help="单套总能量上限（千焦）。默认不限制")
    args = ap.parse_args()

    db = load_db()

    if args.mode == "list":
        if args.json:
            print(json.dumps(db, ensure_ascii=False, indent=2))
            return
        by_cat = {}
        for p in db.values():
            by_cat.setdefault(p["category"], []).append(p["name"])
        for cat in sorted(by_cat):
            print(f"\n【{cat}】")
            for n in sorted(by_cat[cat]):
                print("  -", n)
        print(f"\n共 {len(db)} 个商品")
        return

    rng = random.Random(args.seed)
    used = set()
    results = []

    for i in range(1, args.count + 1):
        items = None
        overflow = None
        # 有能量上限时最多重试 30 次；全部超标则返回最接近的一套并标注超标
        if args.max_kj:
            best = None
            for _ in range(30):
                cand = build_combo(db, rng, want_dessert=not args.no_dessert, used_mains=used)
                if total_kj(cand) <= args.max_kj:
                    items = cand
                    break
                if best is None or total_kj(cand) < total_kj(best):
                    best = cand
            items, overflow = (items, False) if items else (best, True)
        else:
            items = build_combo(db, rng, want_dessert=not args.no_dessert, used_mains=used)

        if items is None:
            print("未能生成符合约束的套餐，请放宽 --max-kj。", file=sys.stderr)
            return
        used.add(items[0]["name"])

        level, summary, detail = review(items)
        payload = {
            "combo_name": combo_name(rng, level),
            "level": level,
            "total_kj": round(total_kj(items)),
            "summary": summary,
            "detail": detail,
            "rhyme": rhyme_mod.build_rhyme(items, level, rng),
            "over_kj_limit": overflow,
            "items": [
                {"name": p["name"], "category": p["category"],
                 "desc": score_desc(p), "nutrition": p["nutrition"], "url": p["url"]}
                for p in items
            ],
        }
        results.append(payload)
        if not args.json:
            print(render(items, rng, idx=None if args.count == 1 else i,
                         name=payload["combo_name"], level=level,
                         summary=summary, detail=detail,
                         overflow=overflow, max_kj=args.max_kj))

    if args.json:
        print(json.dumps(results if args.count > 1 else results[0],
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()