#!/usr/bin/env python3
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def main():
    api_key = os.getenv("DASHSCOPE_API_KEY") or ""
    if not api_key.strip():
        print("[FAIL] DASHSCOPE_API_KEY 未配置")
        return 1

    try:
        from backend.utils.llm_client import llm_client
        from backend.service.embedding_service import get_embedding_service
    except Exception as exc:
        print(f"[FAIL] 模块加载失败: {exc}")
        return 1

    try:
        response = llm_client.chat(
            messages=[{"role": "user", "content": "回复OK即可"}],
            temperature=0,
            max_tokens=16,
            retry_times=1,
        )
        if not response:
            raise ValueError("LLM返回空结果")
        print("[PASS] LLM响应:", response.strip()[:50])
    except Exception as exc:
        print(f"[FAIL] LLM调用失败: {exc}")
        return 1

    try:
        embedding = get_embedding_service().generate_embedding("embedding smoke test")
        if not isinstance(embedding, list) or not embedding:
            raise ValueError("Embedding结果为空")
        print(f"[PASS] Embedding向量长度: {len(embedding)}")
    except Exception as exc:
        print(f"[FAIL] Embedding调用失败: {exc}")
        return 1

    print("[PASS] AI smoke test finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
