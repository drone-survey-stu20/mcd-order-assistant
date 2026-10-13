# MCP 集成说明

本文件说明本项目实际使用的麦当劳 MCP Server、Tool、调用流程与业务价值。

## MCP Server

| 项 | 值 |
|---|---|
| Server 名称 | `mcd-mcp`（麦当劳中国官方托管） |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP |
| 鉴权方式 | 请求头 `Authorization: Bearer <MCP_TOKEN>` |
| 限流 | 每 Token 每分钟最多 600 次请求，超限返回 429 |
| 服务版本 | mcd-mcp 1.0.0（实测握手返回值） |
| 文档 | https://github.com/M-China/mcd-mcp-server |

配置示例见 [`mcp-config.example.json`](mcp-config.example.json)（仅含环境变量占位符，不含真实 Token）。

---

## 本项目使用的 Tool

| Tool | 用途 | 业务价值 |
|---|---|---|
| `now-time-info` | 获取当前完整时间 | 判断处于早餐/午餐/晚餐时段，据此推荐；避免凭模型记忆误判日期 |
| `query-nearby-stores` | 查询附近可用门店 | 定位门店，后续查菜单与下单的前置步骤 |
| `query-meals` | 查询当前门店可售餐品 | **保证推荐的商品真实在售**，避免推荐已下架或当地不供应的品项；获取实时价格 |
| `query-meal-detail` | 餐品详情与套餐组成 | 展开套餐内容、确认可替换项 |
| `list-nutrition-foods` | 餐品营养成分（实测返回 160 项） | 校验套餐总能量，支撑"控能量"场景与 `--max-kj` 约束；同时是商品库的营养来源 |
| `calculate-price` | 计算金额、配送费、优惠、应付总价 | 下单前让用户确认真实花多少钱 |
| `query-store-coupons` | 当前门店可用优惠券 | 点餐时叠加可用优惠 |
| `available-coupons` | 可领取的麦麦省优惠券 | 发现可领优惠，降低点餐成本 |
| `query-my-coupons` | 用户已持有优惠券 | 确认哪些券实际可用 |
| `auto-bind-coupons` | 一键领取麦麦省优惠券 | 一键领券 |
| `campaign-calendar` | 当月营销活动日历 | 活动期商品加权推荐 |
| `order-list` | 历史订单查询 | 与本地点餐记录交叉验证，纠正本地记录 |
| `query-my-account` | 积分账户信息（实测返回麦享会积分数据） | 积分相关建议 |

完整工具说明见 [`references/mcp_tools.md`](references/mcp_tools.md)。

> 本项目**未使用**的工具包括配送地址管理（`delivery-*`）、订单管理（`query-order`/`cancel-order`）、麦麦商城（`mall-*`）、积分抽奖（`query-lottery-info`/`draw-lottery`）、主题活动（`query-party-*`）、团餐助餐（`query-meal-assistance`）。

---

## 调用流程

### 流程 A：场景化推荐

```
用户：随便配个早餐
  │
  ├─→ now-time-info              判断当前是否早餐时段
  ├─→ query-nearby-stores        定位门店
  ├─→ query-meals                取该门店真实在售菜单
  ├─→ list-nutrition-foods       取营养数据
  ├─→ campaign-calendar          检查是否有相关活动，加权推荐
  └─→ 组合方案 + 官网原文卖点 + 营养数据 + 顺口溜
```

**为什么必须走 `query-meals`**：商品库是全量快照，实际在售因门店和时段而异。不查 MCP 就推荐，可能推荐出当地没有的品项。

### 本项目已实测的 MCP 调用

配置 Token 后经WorkBuddy 实测，全部成功：

| 工具 | 返回 |
|---|---|
| `initialize` | `serverInfo: mcd-mcp v1.0.0` |
| `tools/list` | 35 个工具 |
| `now-time-info` | 完整时间 |
| `list-nutrition-foods` | 160 个餐品营养数据 |
| `campaign-calendar` | 7.9KB 活动数据 |
| `query-my-account` | 麦享会积分账户信息 |
| `available-coupons` | 可领券列表 |
| `query-my-coupons` | 已持券列表 |

未实测：`query-nearby-stores` / `query-meals` / `calculate-price` 需门店与商品上下文；`create-order` 涉及真实扣款，按项目设计不代用户执行。

### 流程 B：能量约束推荐

```
用户：想吃得轻一点
  │
  ├─→ list-nutrition-foods       取各商品能量
  ├─→ scripts/combo.py random --max-kj 2500   本地组合并收敛
  ├─→ query-meals                校验组合中每项在售
  └─→ 输出方案（若无法收敛则明确标注超标）
```

### 流程 C：真实下单

```
用户：就这套，帮我下单
  │
  ├─→ query-store-coupons        查可用优惠
  ├─→ calculate-price            算金额/优惠/配送费/应付
  ├─→ ⛔ 复述完整订单给用户，等待明确同意   ← 强制中断点
  ├─→ create-order               用户确认后才调用
  └─→ 返回订单详情与支付链接
```

**`calculate-price` 之后必须停下等用户确认。** 这是本项目不可跳过的安全设计——涉及真实扣款，任何情况下不代替用户做决定。

### 流程 D：点餐记录与偏好

```
用户：我上次点的什么
  │
  ├─→ scripts/orders.py recent <顾客>   读本地记录（主）
  ├─→ order-list                        交叉验证（辅）
  └─→ scripts/orders.py stats           输出偏好，用于下次推荐
```

本地记录为主、官方历史订单为辅：本地记录能附带"微辣"这类 MCP 不返回的口味备注。

---

## 降级策略

MCP 不可用时，核心功能不中断：

| 能力 | MCP 可用 | MCP 不可用 |
|---|---|---|
| 商品推荐 | ✅ 取该门店真实在售 | ⚠️ 降级为本地全量商品库，并提示"以下为通用菜单，实际在售以门店为准" |
| 营养与能量约束 | ✅ 实时校验 | ✅ 本地 `mcd_products.json`（更新至 2025-04） |
| 随机套餐 + 顺口溜 | ✅ | ✅ |
| 点餐记录与偏好 | ✅ | ✅ |
| 优惠券 | ✅ | ❌ 明确告知不可用 |
| 实时价格 | ✅ | ❌ 不报价，明确说明以官方渠道为准 |
| 真实下单 | ✅ | ❌ 只输出推荐方案 |

调用报错时的处理：
- **401**：Token 无效或过期，提示用户检查配置，**不重试**
- **429**：触发限流，降低频率后稍后再试，**不连续重试**

---

## 业务价值

**对用户**：把"今天吃啥"的决策成本从"翻菜单 + 纠结"压缩到"看一眼方案 + 确认"。所有卖点来自官网原文，营养数据透明，不用担心被夸大宣传。

**对门店**：推荐基于该门店真实在售菜单，减少"推荐了但买不到"的失败体验；同时通过 `query-store-coupons` 引导使用优惠券，提升客单转化。

**对 MCP 生态**：本项目是 `query-meals` + `list-nutrition-foods` + `calculate-price` 的组合使用范例，展示了如何把点餐类 MCP 从"能下单"扩展到"能做决策辅助"。
