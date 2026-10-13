# -*- coding: utf-8 -*-
"""从麦当劳 MCP list-nutrition-foods 拉取官方营养数据，输出结构化 JSON。

MCP 返回的是形如：
  [160]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
    猪柳麦满分,null,1288,308,16,16,24,781,213
  的自定义序列化格式，需解析后转为 JSON。

用法：
    export MCD_MCP_TOKEN=xxx
    python fetch_nutrition.py > mcp_nutrition.json
"""
import json
import os
import re
import sys
import urllib.request

MCP_URL = "https://mcp.mcd.cn"
TOKEN = os.environ.get("MCD_MCP_TOKEN", "")


def rpc(method, params, req_id=1):
    """向 MCP Server 发起一次 JSON-RPC 调用，返回解析后的响应。"""
    payload = json.dumps({
        "jsonrpc": "2.0", "id": req_id, "method": method, "params": params,
    }).encode()
    req = urllib.request.Request(MCP_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    req.add_header("MCP-Protocol-Version", "2024-11-05")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
    # Streamable HTTP 可能返回 SSE 格式
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            raw = line[5:]
            break
    return json.loads(raw)


def parse_csv(data):
    """解析 MCP 的 [N]{fields}: 行1\\n行2 格式。"""
    header = re.search(r"\]\{(.*?)\}:\s*(.*)", data, re.S)
    if not header:
        return [], []
    fields = header.group(1).split(",")
    rows = []
    for line in header.group(2).split("\n"):
        line = line.strip()
        if not line or "," not in line:
            continue
        parts = line.split(",")
        if len(parts) < len(fields):
            continue
        row = {}
        for f, v in zip(fields, parts):
            v = v.strip()
            if v == "null":
                row[f] = None
            elif re.match(r"^-?\d+(\.\d+)?$", v):
                row[f] = float(v) if "." in v else int(v)
            else:
                row[f] = v
        if row.get("productName"):
            rows.append(row)
    return fields, rows


def main():
    if not TOKEN:
        print("错误：请先设置环境变量 MCD_MCP_TOKEN", file=sys.stderr)
        sys.exit(1)

    # MCP 需先 initialize 再调用工具
    rpc("initialize", {
        "protocolVersion": "2024-11-05", "capabilities": {},
        "clientInfo": {"name": "mcd-order-assistant", "version": "1.0"},
    })
    try:
        rpc("notifications/initialized", {}, req_id=0)
    except Exception:
        pass

    resp = rpc("tools/call", {"name": "list-nutrition-foods", "arguments": {}}, req_id=2)

    text = "".join(c.get("text", "") for c in resp["result"]["content"])
    # 外层是 {success,data} 包裹，data 才是那段 CSV
    outer = None
    m = re.search(r'\{"success".*\}', text, re.S)
    if m:
        try:
            outer = json.loads(m.group(0))
        except json.JSONDecodeError:
            outer = None
    payload = outer["data"] if outer and isinstance(outer.get("data"), str) else text

    fields, rows = parse_csv(payload)
    out = {
        "source": "mcd-mcp:list-nutrition-foods",
        "fields": fields,
        "count": len(rows),
        "items": rows,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()