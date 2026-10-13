# -*- coding: utf-8 -*-
"""抓取麦当劳官网产品页，提取商品名/描述/营养成分，输出 JSON。"""
import re, html, json, os, glob

SRC = "mcd_pages"
OUT = "mcd_products.json"

def text_of(raw):
    s = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', raw)
    s = html.unescape(re.sub(r'(?s)<[^>]+>', ' ', s))
    return re.sub(r'\s+', ' ', s).strip()

def field(t, label):
    m = re.search(label + r'\s*([\d.]+)\s*(千焦|克|毫克|千卡)', t)
    return (m.group(1) + m.group(2)) if m else None

items, skipped = {}, []
for path in sorted(glob.glob(os.path.join(SRC, "*.html"))):
    slug = os.path.splitext(os.path.basename(path))[0]
    raw = open(path, encoding="utf-8", errors="ignore").read()

    # 详情块：<h3>产品名</h3> 紧跟 <p class="detail">官方描述
    m = re.search(r'<h3[^>]*>([^<]+)</h3>\s*<p class="detail">(.*?)</p>', raw, re.S)
    if not m:
        skipped.append(slug)
        continue

    name = html.unescape(m.group(1)).strip()
    desc = text_of(m.group(2))

    t = text_of(raw)
    items[slug] = {
        "slug": slug,
        "name": name,
        "category": ("早餐" if "早餐" in raw[:800] else
                     "小食" if any(k in name for k in ("薯条", "鸡翅", "麦乐鸡", "鸡排", "玉米", "苹果片", "V翅")) else
                     "甜品" if any(k in name for k in ("新地", "派", "旋风", "圆筒")) else
                     "饮品" if ("可乐" in name or "咖啡" in name or "茶" in name or "牛奶" in name) else
                     "汉堡"),
        "desc": desc,
        "nutrition": {
            "能量": field(t, "能量"), "蛋白质": field(t, "蛋白质"),
            "脂肪": field(t, "脂肪"), "碳水化合物": field(t, "碳水化合物"),
            "钠": field(t, "钠"), "钙": field(t, "钙"),
        },
        "url": "https://www.mcdonalds.com.cn/product/" + slug,
    }

json.dump(items, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("parsed:", len(items), "| skipped:", skipped)
for v in items.values():
    print(f"{v['name']} | {v['category']} | {v['nutrition']['能量']} | {v['desc'][:40]}")