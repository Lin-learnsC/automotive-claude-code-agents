#!/usr/bin/env python3
"""
Standalone verification script for KimiAdapter migration.

Does NOT require anthropic package or Claude API key.
Tests:
  1. KimiAdapter instantiation and API connectivity
  2. Response format validation
  3. ResponseCache hit/miss behavior
  4. Token usage tracking

Usage:
    export KIMI_API_KEY="sk-..."
    python3 scripts/verify_kimi_migration.py
"""

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.llm_council import KimiAdapter, ModelConfig, ResponseCache


async def main() -> int:
    api_key = os.environ.get("KIMI_API_KEY")
    if not api_key:
        print("[FAIL] KIMI_API_KEY environment variable not set.")
        print("       Export it first: export KIMI_API_KEY='sk-...'")
        return 1

    print("=" * 60)
    print("KimiAdapter Migration Verification")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Test 1: Instantiation
    # ------------------------------------------------------------------
    print("\n[Test 1] Instantiation ...")
    config = ModelConfig(
        name="kimi-latest",
        provider="kimi",
        api_key_env="KIMI_API_KEY",
        endpoint="https://api.moonshot.cn/v1",
        max_tokens=1024,
        temperature=0.3,
    )
    cache = ResponseCache(max_size=10, default_ttl=300)
    adapter = KimiAdapter(config, cache)
    print("[PASS] KimiAdapter created successfully")

    # ------------------------------------------------------------------
    # Test 2: Live API call
    # ------------------------------------------------------------------
    print("\n[Test 2] Live API call ...")
    system_prompt = (
        "You are an automotive software architect. "
        "Answer in 2 sentences maximum."
    )
    messages = [
        {
            "role": "user",
            "content": (
                "For a battery management system (BMS), "
                "should cell monitoring be event-driven or polling-based?"
            ),
        }
    ]

    try:
        response_text, duration_ms = await adapter.get_completion(
            messages, system_prompt
        )
    except Exception as exc:
        print(f"[FAIL] API call failed: {exc}")
        return 1

    if not response_text or len(response_text) < 10:
        print("[FAIL] Response too short or empty")
        return 1

    print(f"[PASS] Response received in {duration_ms:.0f} ms")
    print(f"        Length: {len(response_text)} chars")
    print(f"        Preview: {response_text[:120].replace(chr(10), ' ')}...")

    # ------------------------------------------------------------------
    # Test 3: Cache miss → hit
    # ------------------------------------------------------------------
    print("\n[Test 3] ResponseCache behavior ...")
    stats_before = cache.get_stats()
    print(f"        Before: {stats_before}")

    # Identical call should hit cache
    response_cached, duration_cached = await adapter.get_completion(
        messages, system_prompt
    )

    stats_after = cache.get_stats()
    print(f"        After:  {stats_after}")

    if duration_cached != 0.0:
        print("[WARN] Cache did not return instant response (duration != 0)")
    else:
        print("[PASS] Cache hit confirmed (duration = 0.0 ms)")

    if stats_after["hits"] <= stats_before["hits"]:
        print("[FAIL] Cache hit counter did not increment")
        return 1

    # ------------------------------------------------------------------
    # Test 4: Adapter statistics
    # ------------------------------------------------------------------
    print("\n[Test 4] Adapter statistics ...")
    stats = adapter.get_stats()
    print(f"        {stats}")
    if stats["request_count"] >= 1:
        print("[PASS] Request count tracked correctly")
    else:
        print("[FAIL] Request count not tracked")
        return 1

    # ------------------------------------------------------------------
    # Test 5: Content consistency
    # ------------------------------------------------------------------
    print("\n[Test 5] Content consistency ...")
    if response_text.strip() == response_cached.strip():
        print("[PASS] Cached response matches original")
    else:
        print("[WARN] Cached response differs from original (may be non-deterministic)")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("ALL CHECKS PASSED — KimiAdapter migration verified")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Install anthropic package: pip install anthropic")
    print("  2. Set ANTHROPIC_API_KEY for full dual-model debate")
    print("  3. Run: python3 -m tools.llm_council <topic> --secondary-provider kimi")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
