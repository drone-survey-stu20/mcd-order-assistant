# 麦当劳 MCP Server 工具参考

> 来源：官方文档 https://github.com/M-China/mcd-mcp-server+ 实测 `tools/list` 返回。
> MCP Server 实测握手版本 mcd-mcp 1.0.0，实际提供 35 个工具（官方文档列出 38 个，含`query-promotions`、`query-survey-coupon` 等文档未收录项）。
> 本文件为本技能实际调用的工具清单，未列出的工具不代表项目使用了。
>
> ✅ 表示已通过真实调用验证。

## 本项目实际使用的工具

| 工具 | 用途 | 在本项目中的场景 |
|---|---|---|
| `list-nutrition-foods` ✅ | 餐品营养成分（实测返回 **160 个餐品**） | 商品库营养来源、校验套餐能量、支撑"控能量"场景 |
| `query-meals` | 查询门店在售餐品（分类、编码、标签） | 确认推荐商品在售、获取实时价格 |
| `query-meal-detail` | 餐品详情与套餐组成 | 查看套餐含什么、有哪些可替换项 |
| `query-nearby-stores` | 查询附近可用门店 | 下单前定位门店 |
| `calculate-price` | 计算商品金额、配送费、优惠、应付总价 | 下单前给用户确认金额 |
| `query-store-coupons` | 当前门店可用优惠券 | 点餐时叠加优惠 |
| `available-coupons` ✅ | 可领取的麦麦省优惠券 | 发现可领优惠 |
| `query-my-coupons` ✅ | 用户已持有的优惠券 | 确认可用券 |
| `auto-bind-coupons` | 一键领取麦麦省优惠券 | 一键领券（涉及账号写操作，需用户确认） |
| `campaign-calendar` ✅ | 当月营销活动日历（实测 7.9KB 数据） | 活动加权推荐 |
| `now-time-info` ✅ | 获取当前完整时间 | 判断"早餐/午餐/晚餐"时段、日期判断 |
| `order-list` | 历史订单查询 | 与本地点餐记录交叉验证 |
| `query-my-account` ✅ | 积分账户信息（实测麦享会积分数据） | 积分建议 |

## 实测覆盖

已通过真实 Token 验证 ✅：`initialize`、`tools/list`、`now-time-info`、`list-nutrition-foods`、`campaign-calendar`、`query-my-account`、`available-coupons`、`query-my-coupons`

未实测（需额外上下文或涉及真实交易）：`query-nearby-stores`、`query-meals`、`query-meal-detail`、`query-store-coupons`、`calculate-price`、`create-order`、`cancel-order`

## 调用原则

1. **价格、库存、优惠券一律实时查 MCP**，不得用本地数据或记忆作答。本地 `mcd_products.json` 只用于商品卖点原文与营养基线。
2. **下单前必须 `calculate-price`**，把金额、优惠、配送费完整念给用户确认后再 `create-order`。
3. **限流友好**：每 Token 每分钟上限 600 次请求。同一轮对话内复用已获取的结果（如门店列表只查一次），不做无意义的重复查询。
4. **时段判断调 `now-time-info`**，不要凭模型记忆推断日期时间。
5. 调用失败时（401/429）不要反复重试，告知用户原因后降级。

## 错误码

| code | 原因 | 处理 |
|---|---|---|
| 401 | Token 无效/过期/未提供 | 检查配置，不重试 |
| 429 | 超过 600 次/分钟 | 降低频率，稍后再试 |

## 未使用的工具（部分列出）

`delivery-*`（配送地址管理）、`query-order`/`cancel-order`（订单管理）、`mall-*`（麦麦商城）、`query-lottery-info`/`draw-lottery`（积分抽奖）、`query-party-*`/`party-order-create`（主题活动）、`query-meal-assistance`（团餐助餐）在本项目中未被调用。
