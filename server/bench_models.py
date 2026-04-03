#!/usr/bin/env python3
"""Benchmark: ultra (27B) vs smart9 (9B) model speed."""

import httpx
import time
import asyncio
import sys

BASE = "http://localhost:8000"

TESTS = [
    {"name": "短回覆", "msg": "你好"},
    {"name": "中回覆", "msg": "你喜歡吃什麼？"},
    {"name": "長回覆", "msg": "請詳細描述一下你理想中的約會是什麼樣子"},
    {"name": "工具關鍵字", "msg": "幫我讀最新email"},
    {"name": "工具關鍵字2", "msg": "幫我排行程"},
]


async def bench(client_id: str, message: str):
    """Benchmark via REST API — measures total round-trip time."""
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=120) as http:
        resp = await http.post(
            f"{BASE}/api/chat",
            json={"message": message, "language": "zh-TW", "client_id": client_id},
        )
        data = resp.json()
    total = time.perf_counter() - t0
    text = data.get("text", "")
    mode = data.get("mode", "?")
    return {
        "total": total,
        "chars": len(text),
        "mode": mode,
        "text_preview": text[:60],
    }


async def run_bench(label: str):
    print(f"\n{'=' * 60}")
    print(f"  Model: {label}")
    print(f"{'=' * 60}")
    print(f"{'測試':<12s} {'模式':<8s} {'總計(s)':>8s} {'字數':>6s} {'字/s':>6s}")
    print("-" * 50)

    for i, t in enumerate(TESTS):
        r = await bench(f"bench_{label}_{i}", t["msg"])
        speed = r["chars"] / r["total"] if r["total"] > 0 else 0
        print(
            f"{t['name']:<12s} {r['mode']:<8s} {r['total']:>8.1f} "
            f"{r['chars']:>6d} {speed:>6.1f}"
        )
        # Small delay between requests
        await asyncio.sleep(1)


async def main():
    model = sys.argv[1] if len(sys.argv) > 1 else None
    if model:
        await run_bench(model)
    else:
        for m in ["smart9", "ultra"]:
            await run_bench(m)


if __name__ == "__main__":
    asyncio.run(main())
