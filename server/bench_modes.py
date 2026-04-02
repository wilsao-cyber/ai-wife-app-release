"""Benchmark: chat vs auto vs assist mode speed."""

import httpx
import time
import json
import asyncio

BASE = "http://localhost:8000"

TESTS = [
    {
        "name": "聊天模式 (chat)",
        "message": "你好，今天天氣如何？",
        "mode": "chat",
    },
    {
        "name": "自動模式 (auto) — 純聊天",
        "message": "你喜歡吃什麼？",
        "mode": "auto",
    },
    {
        "name": "協助模式 (assist)",
        "message": "幫我排行程",
        "mode": "assist",
    },
    {
        "name": "自動模式 (auto) — 工具關鍵字",
        "message": "幫我讀最新email",
        "mode": "auto",
    },
]


async def bench_stream(test: dict, client_id: str):
    mode_override = None if test["mode"] == "auto" else test["mode"]
    payload = {
        "message": test["message"],
        "language": "zh-TW",
        "client_id": client_id,
    }
    if mode_override:
        payload["mode_override"] = mode_override

    t0 = time.perf_counter()
    first_chunk = None
    total_chunks = 0
    full_text = ""

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST", f"{BASE}/api/chat/stream", json=payload
        ) as resp:
            buf = ""
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if not data:
                    continue
                try:
                    evt = json.loads(data)
                except json.JSONDecodeError:
                    continue

                if evt.get("type") == "chunk":
                    if first_chunk is None:
                        first_chunk = time.perf_counter() - t0
                    full_text += evt.get("data", "")
                    total_chunks += 1
                elif evt.get("type") == "done":
                    if not full_text:
                        full_text = evt.get("text", "")
                    break

    total = time.perf_counter() - t0
    return {
        "name": test["name"],
        "ttfb": first_chunk,
        "total": total,
        "chars": len(full_text),
        "tokens": total_chunks,
        "tokens_per_sec": total_chunks / total if total > 0 else 0,
    }


async def main():
    print(
        f"{'模式':<30s} {'首字(s)':>8s} {'總計(s)':>8s} {'字數':>6s} {'chunks':>6s} {'tok/s':>6s}"
    )
    print("-" * 72)

    for i, test in enumerate(TESTS):
        result = await bench_stream(test, f"bench_{i}")
        ttfb = f"{result['ttfb']:.2f}" if result["ttfb"] is not None else "N/A"
        print(
            f"{result['name']:<30s} {ttfb:>8s} {result['total']:>8.2f} "
            f"{result['chars']:>6d} {result['tokens']:>6d} {result['tokens_per_sec']:>6.1f}"
        )


if __name__ == "__main__":
    asyncio.run(main())
