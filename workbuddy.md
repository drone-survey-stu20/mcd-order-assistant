# WorkBuddy 开发记录

本文件记录本项目通过腾讯 WorkBuddy 智能体完成的开发过程，作为联动活动奖励的核验材料。

## 开发环境

| 项 | 值 |
|---|---|
| 工具 | 腾讯 WorkBuddy |
| 开发语言 | Python 3.13（仅标准库，无第三方依赖） |
| MCP 配置位置 | `~/.workbuddy/mcp.json` |
| 麦当劳 MCP 端点 | `https://mcp.mcd.cn`（Streamable HTTP） |

## 开发阶段

### 阶段一：调研与可行性验证

**目标**：确认麦当劳 MCP 能力边界与赛事规格。

**WorkBuddy 执行的关键动作**：

1. 搜索并抓取麦当劳开放平台文档（`https://open.mcd.cn/mcp`），确认为远程托管 MCP Server，非 WorkBuddy 连接器市场中的连接器，需手工配置到 `~/.workbuddy/mcp.json`
2. 读取活动官方仓库 `M-China/mcd-developer-innovation-challenge`，下载 `activityGuidelines.md` 与 `CONTEST_DECLARATION.md` 原文
3. 读取官方 MCP 文档仓库 `M-China/mcd-mcp-server`，获取工具清单与错误码说明

**关键发现**：

- 赛事规则第 16 条明确禁止「宣扬不健康饮食方式、奢靡浪费」与「贬低麦当劳品牌」。项目初版顺口溜文案中的「深夜放纵」「管他明天胖不胖」「中国胃认证」正好命中该条款，主动全部改写为「今天想吃顿好的」「这一顿吃值了」「风味到位」
- 规则第 14 条要求仓库创建时间在 2025-12-25 至 2026-10-25 之间
- 规则第 21 条要求「真实使用麦当劳 MCP 能力」，因此 MCP 不可降级为纯本地实现

### 阶段二：技能设计与实现

基于 WorkBuddy 读取本地已安装的高质量 Skill 源码，吸收设计手法：

| 参考对象 | 借鉴点 |
|---|---|
| `westock-tool`（31KB，垂类选品） | 意图路由表、禁止事项、数据源优先级、降级前告知用户 |
| `excel-generation`（参数化工作流） | 明确的适用/拒绝条件，防止技能越界 |
| `neodata-financial-search`（推荐类） | description 密集堆触发词、场景速查表 |

据此完成：

- `SKILL.md`：意图路由表（区分「随机来一套」与「推荐一下」）、禁止事项、MCP 降级策略
- `scripts/combo.py`：随机套餐生成，含能量约束与 JSON 输出
- `scripts/rhyme.py`：按热量档位选韵脚的顺口溜生成器
- `scripts/orders.py`：点餐记录与偏好统计，含商品名校验
- `references/recipes.md`：六类场景化搭配

### 阶段三：官网商品数据抓取

**目标**：保证商品卖点来自官网原文，杜绝编造。

WorkBuddy 通过 sitemap 定位全部 `/product/` 页面，批量抓取后定位产品页 DOM 结构 `<h3>名称</h3><p class="detail">官网描述</p>`，解析出 29 个在售商品的官方描述与营养成分。

> 注：首版正则匹配到导航栏残留文字，修正定位方式后得到干净原文。

### 阶段四：接入 MCP 真实数据（关键升级）

配置 Token 后，通过 WorkBuddy 实测 MCP 端点：

```
initialize       → serverInfo: mcd-mcp v1.0.0
tools/list       → 35 个工具
list-nutrition-foods → 160 个餐品官方营养数据
now-time-info    → 正常返回
```

**重要发现**：MCP 返回的营养数据（160 项）远超官网可抓取的 29 项，新增覆盖：

- 早餐类 17 项（麦满分系列、炒双蛋堡、早安营养卷、粥品）
- 儿童餐 7 项（果然多肉、牛气满满、绝代双翅等）
- 咖啡与茶饮 74 项
- 沙拉 2 项

而官网完全不提供这些品项。这意味着初版「商品库未收录早餐 SKU」的缺陷可通过 MCP 彻底解决。

**实现**：

- `scripts/fetch_nutrition.py` — 解析 MCP 的自定义序列化格式（`[160]{fields}: 行1\n行2`），输出结构化 JSON
- `scripts/merge_catalog.py` — 合并官网卖点与 MCP 营养为统一 `catalog.json`
  - 名称按规格差异显式映射（官网「薯条」↔ MCP「中薯条」），不做猜测合并
  - 卖点只从官网取；MCP 独有品项描述留空，运行时标注「官网暂无描述」，**不编造卖点**

### 阶段五：合规复核与回归测试

WorkBuddy 执行三轮自检：

1. **合规扫描** — 扫描「放纵/胖不胖/不谈热量/奢靡/浪费」等违规表述，全部清除
2. **敏感信息扫描** — 确认仓库不含真实 Token，`mcp-config.example.json` 仅含 `${MCD_MCP_TOKEN}` 占位符，`data/` 用户数据已由 `.gitignore` 排除
3. **功能回归** — combo.py 六种参数组合 + orders.py 三种命令全部通过

## MCP 真实调用记录

配置 Token 后，通过 WorkBuddy 实测麦当劳 MCP Server，全部成功：

| 工具 | 状态 | 返回 | 用途 |
|---|---|---|---|
| `initialize` | ✅ 200 | `serverInfo: mcd-mcp v1.0.0` | 协议握手 |
| `tools/list` | ✅ 200 | 35 个工具 | 工具清单 |
| `now-time-info` | ✅ 200 | 完整时间 | 时段判断 |
| `list-nutrition-foods` | ✅ 200 | 160 个餐品营养数据 | 营养基线 |
| `campaign-calendar` | ✅ 200 | 7981 字符活动数据 | 活动加权推荐 |
| `query-my-account` | ✅ 200 | 麦享会积分账户信息 | 积分建议 |
| `available-coupons` | ✅ 200 | 2727 字符可领券列表 | 领券引导 |
| `query-my-coupons` | ✅ 200 | 1263 字符已持券列表 | 确认可用券 |

## 未实测工具

以下需用户位置、门店或产生真实交易，未在本项目实测：

- `query-nearby-stores` / `query-meals` / `query-meal-detail` / `query-store-coupons` — 需门店上下文
- `calculate-price` — 需具体商品清单
- `create-order` / `cancel-order` — **真实扣款操作，按项目设计不代用户执行**
- `mall-*` / `query-lottery-*` / `query-party-*` / `delivery-*` — 本项目未使用

## 声明

本项目开发全程使用腾讯 WorkBuddy 智能体完成，包括：赛事规则调研、竞品 Skill 设计手法分析、官网数据抓取、代码实现与调试、MCP 端点实测、合规复核与回归测试。
