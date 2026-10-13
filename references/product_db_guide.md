# 商品库结构与维护

数据文件：`references/mcd_products.json`

## 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `slug` | string | URL 标识，对应官网产品页路径末段 |
| `name` | string | 官方产品名（中文） |
| `category` | string | 汉堡 / 小食 / 甜品 / 饮品 / 早餐 |
| `desc` | string | **官网产品描述原文**，推荐话术的唯一依据 |
| `nutrition` | object | 能量、蛋白质、脂肪、碳水化合物、钠、钙 |
| `url` | string | 官网产品页链接 |

营养数据标注口径：单份计量，更新至 2025 年 4 月，由国家认可实验室测定，实际供应可能因批次与产地略有差异。

## 铁律

1. **`desc` 必须是官网原文，禁止改写或编造**。向用户介绍商品优点时直接引用或截取原句。
2. **商品库不含价格**。价格随门店、时段、活动变动，一律以麦当劳 MCP 或官方渠道为准，不要给出具体金额。
3. **库中没有的商品不要臆造**。先 WebFetch 官网查证，查不到就如实说不确定。

## 更新流程

```bash
# 1. 抓取官网 sitemap，找出所有产品页
curl -s https://www.mcdonalds.com.cn/sitemap.xml | grep -oE '<loc>[^<]+</loc>' | sed 's/<[^>]*>//g' | grep '/product/'

# 2. 逐页下载 HTML 快照到 mcd_pages/<slug>.html

# 3. 运行提取脚本覆盖商品库
python scripts/build_products.py
```

提取依赖产品页的 DOM 结构：`<h3>产品名</h3><p class="detail">官网描述</p>`。若麦当劳改版导致解析失败（`parsed: 0`），需先检查 HTML 结构再调整正则。

`scripts/build_products.py` 分类导航页（`hamburgers`、`beverage`、`Snacks` 等 6 个）会被自动跳过，属正常现象。

## 更新后必做

抽查 2-3 条记录，确认 `desc` 是通顺的官网文案而非导航残留文字。