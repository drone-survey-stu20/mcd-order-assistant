# -*- coding: utf-8 -*-
"""麦当劳点餐记录管理：记录点餐次数、购买明细、统计偏好。

用法:
    python orders.py add小王 --items 巨无霸,麦辣鸡腿汉堡 --combo 辣味双拼 --note 微辣
    python orders.py stats 小王
    python orders.py recent 小王
    python orders.py list
"""
import argparse
import json
import os
from collections import Counter
from datetime import date

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
ORDERS_PATH = os.path.join(DATA_DIR, "orders.json")
DB_PATH = os.path.join(BASE, "references", "mcd_products.json")


def load():
    if os.path.exists(ORDERS_PATH):
        with open(ORDERS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"customers": {}}


def save(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ORDERS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def category_map():
    """商品名 -> 分类，用于统计偏好。"""
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)
    return {p["name"]: p["category"] for p in db.values()}


def validate_items(items):
    """校验商品名是否在商品库中，返回 (有效列表, 不认识的名字列表)。

    记录报错名字会导致统计失真，因此入库前必须提示用户确认。
    """
    cmap = category_map()
    if not cmap:  # 商品库不可用时不做校验，避免误伤
        return items, []
    ok, unknown = [], []
    for name in items:
        (ok if name in cmap else unknown).append(name)
    return ok, unknown


def cmd_add(args):
    data = load()
    customers = data["customers"]
    who = args.customer
    rec = customers.setdefault(who, {"total_visits": 0, "last_visit": None, "history": []})

    items = [x.strip() for x in args.items.split(",") if x.strip()] if args.items else []
    items, unknown = validate_items(items)
    if unknown:
        print(f"⚠️ 以下商品不在商品库中，未计入统计：{'、'.join(unknown)}")
        print("   （可能是新品或已下架，如确实是新品可忽略此提示）")

    rec["history"].append({
        "date": args.date or date.today().isoformat(),
        "items": items,
        "unrecognized": unknown,
        "combo_name": args.combo or "",
        "note": args.note or "",
    })
    rec["total_visits"] += 1
    rec["last_visit"] = args.date or date.today().isoformat()
    save(data)
    print(f"✅ 已记录 {who} 的第 {rec['total_visits']} 次点餐："
          f"{'、'.join(items) if items else '（未填明细）'}")
    return rec


def cmd_stats(args):
    data = load()
    who = args.customer
    rec = data["customers"].get(who)
    if not rec:
        print(f"还没有 {who} 的点餐记录。")
        return

    counter = Counter()
    for h in rec["history"]:
        counter.update(h["items"])

    print(f"\n👤 {who}")
    print(f"总点餐次数：{rec['total_visits']} 次")
    print(f"最近一次：{rec.get('last_visit') or '—'}")

    if counter:
        print("\n最常点：")
        for name, n in counter.most_common(5):
            print(f"  · {name} × {n}")

        cmap = category_map()
        cats = Counter(cmap.get(i, "其他") for i in counter.elements())
        top_cat, top_n = cats.most_common(1)[0]
        print(f"\n口味偏好：偏{top_cat}（{top_n}/{sum(cats.values())} 项）")

    combos = [h["combo_name"] for h in rec["history"] if h["combo_name"]]
    if combos:
        print(f"点过的套餐：{'、'.join(sorted(set(combos)))}")


def cmd_recent(args):
    data = load()
    rec = data["customers"].get(args.customer)
    if not rec or not rec["history"]:
        print(f"还没有 {args.customer} 的点餐记录。")
        return
    n = args.n
    print(f"\n🧾 {args.customer} 最近 {n} 条点餐记录：")
    for h in rec["history"][-n:][::-1]:
        items = "、".join(h["items"]) or "（未填明细）"
        line = f"  {h['date']}｜{items}"
        if h["combo_name"]:
            line += f"｜套餐：{h['combo_name']}"
        if h["note"]:
            line += f"｜备注：{h['note']}"
        print(line)


def cmd_list(args):
    data = load()
    customers = data["customers"]
    if not customers:
        print("还没有任何点餐记录。")
        return
    print(f"\n📋 共{len(customers)} 位顾客：")
    for who, rec in sorted(customers.items(),
                           key=lambda kv: kv[1].get("last_visit") or "",
                           reverse=True):
        last = rec.get("last_visit") or "—"
        print(f"  · {who}：{rec['total_visits']} 次，最近 {last}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="记录一次点餐")
    a.add_argument("customer")
    a.add_argument("--items", help="商品，逗号分隔")
    a.add_argument("--combo", help="套餐名")
    a.add_argument("--note", help="备注，如口味偏好")
    a.add_argument("--date", help="日期 YYYY-MM-DD，默认今天")
    a.set_defaults(func=cmd_add)

    s = sub.add_parser("stats", help="统计偏好")
    s.add_argument("customer")
    s.set_defaults(func=cmd_stats)

    r = sub.add_parser("recent", help="最近记录")
    r.add_argument("customer")
    r.add_argument("-n", type=int, default=3)
    r.set_defaults(func=cmd_recent)

    l = sub.add_parser("list", help="顾客概览")
    l.set_defaults(func=cmd_list)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()