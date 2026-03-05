"""
Embedding生成服务
支持 OpenAI 兼容网关与 DashScope SDK 两种调用风格。
"""
import logging
from typing import Any, Dict, List, Optional

import dashscope
from openai import OpenAI

from backend.config.config import settings

logger = logging.getLogger(__name__)


def _normalize_base_url(url: str) -> str:
    return (url or "").strip().rstrip("/")


def _resolve_embedding_api_base() -> str:
    """解析 embedding 网关地址（优先级：新变量 > 旧变量 > LLM网关）。"""
    base = _normalize_base_url(getattr(settings, "EMBEDDING_API_BASE", ""))
    if base:
        return base

    legacy = _normalize_base_url(getattr(settings, "DASHSCOPE_EMBEDDING_API_BASE", ""))
    if legacy:
        return legacy

    llm_base = _normalize_base_url(getattr(settings, "DASHSCOPE_API_BASE", ""))
    if llm_base:
        return llm_base

    return "https://dashscope.aliyuncs.com/compatible-mode/v1"


def _resolve_dashscope_http_base(base_url: str) -> str:
    """
    解析 DashScope SDK HTTP 地址。

    DashScope SDK 默认使用 /api/v1，若提供 compatible-mode 地址需要自动改写。
    """
    normalized = _normalize_base_url(base_url)
    if normalized.endswith("/compatible-mode/v1"):
        return normalized[: -len("/compatible-mode/v1")] + "/api/v1"
    return normalized


def _pick_embedding_api_style(configured_style: str, base_url: str) -> str:
    style = str(configured_style or "auto").strip().lower()
    if style in {"openai", "dashscope"}:
        return style

    normalized = _normalize_base_url(base_url)
    if "/compatible-mode/" in normalized or normalized.endswith("/api/v1"):
        return "dashscope"
    return "openai"


def _safe_preview(text: str, max_len: int = 200) -> str:
    value = str(text or "").replace("\n", " ").replace("\r", " ").strip()
    return value[:max_len]


def _extract_openai_error_fields(exc: Exception) -> Dict[str, Optional[str]]:
    status_code: Optional[str] = None
    error_code: Optional[str] = None
    request_id: Optional[str] = None
    message = str(exc)

    raw_status = getattr(exc, "status_code", None)
    if raw_status is not None:
        status_code = str(raw_status)

    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            if err.get("code") is not None:
                error_code = str(err.get("code"))
            if err.get("message"):
                message = str(err.get("message"))

    if getattr(exc, "request_id", None):
        request_id = str(getattr(exc, "request_id"))

    response = getattr(exc, "response", None)
    if response is not None:
        headers = getattr(response, "headers", None)
        if headers:
            request_id = request_id or str(headers.get("x-request-id") or headers.get("x-requestid") or "")
        if status_code is None and getattr(response, "status_code", None) is not None:
            status_code = str(getattr(response, "status_code"))

    return {
        "status_code": status_code,
        "error_code": error_code,
        "request_id": request_id or None,
        "message": message,
    }


class EmbeddingService:
    """Embedding生成服务"""

    # 兼容旧代码对类属性的读取
    MODEL = settings.EMBEDDING_MODEL
    DIM = settings.EMBEDDING_DIM

    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY未配置")

        self.model = settings.EMBEDDING_MODEL
        self.timeout = int(getattr(settings, "LLM_TIMEOUT", 120))
        self.embedding_api_base = _resolve_embedding_api_base()
        self.configured_api_style = str(getattr(settings, "EMBEDDING_API_STYLE", "auto")).strip().lower() or "auto"
        self.api_style = _pick_embedding_api_style(self.configured_api_style, self.embedding_api_base)
        self.dashscope_http_base = _resolve_dashscope_http_base(self.embedding_api_base)

        self._openai_client = OpenAI(
            api_key=self.api_key,
            base_url=self.embedding_api_base,
        )
        dashscope.api_key = self.api_key
        dashscope.base_http_api_url = self.dashscope_http_base

        logger.info(
            "Embedding服务初始化完成: model=%s style=%s base=%s dashscope_base=%s",
            self.model,
            self.api_style,
            self.embedding_api_base,
            self.dashscope_http_base,
        )

    def _build_error_message(
        self,
        *,
        action: str,
        style: str,
        base_url: str,
        message: str,
        status_code: Optional[str] = None,
        error_code: Optional[str] = None,
        request_id: Optional[str] = None,
        batch_no: Optional[int] = None,
        preview: str = "",
    ) -> str:
        parts = [
            f"{action}失败",
            f"style={style}",
            f"base={base_url}",
            f"model={self.model}",
            f"status={status_code or 'unknown'}",
            f"code={error_code or 'unknown'}",
            f"request_id={request_id or 'unknown'}",
            f"message={message or 'unknown'}",
        ]
        if batch_no is not None:
            parts.append(f"batch_no={batch_no}")
        if preview:
            parts.append(f"input_preview={preview}")
        return "; ".join(parts)

    def _style_attempt_order(self) -> List[str]:
        if self.configured_api_style == "auto":
            if self.api_style == "openai":
                return ["openai", "dashscope"]
            return ["dashscope", "openai"]
        return [self.api_style]

    def _generate_with_openai(self, text: str, batch_no: Optional[int] = None) -> List[float]:
        preview = _safe_preview(text)
        try:
            response = self._openai_client.embeddings.create(
                model=self.model,
                input=text,
                timeout=self.timeout,
            )
            data = getattr(response, "data", None) or []
            if not data:
                raise RuntimeError("openai返回空data")

            first = data[0]
            embedding = getattr(first, "embedding", None)
            if embedding is None and isinstance(first, dict):
                embedding = first.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                raise RuntimeError("openai返回embedding为空")
            return embedding
        except RuntimeError:
            raise
        except Exception as exc:
            fields = _extract_openai_error_fields(exc)
            raise RuntimeError(
                self._build_error_message(
                    action="生成embedding",
                    style="openai",
                    base_url=self.embedding_api_base,
                    status_code=fields.get("status_code"),
                    error_code=fields.get("error_code"),
                    request_id=fields.get("request_id"),
                    message=fields.get("message") or str(exc),
                    batch_no=batch_no,
                    preview=preview,
                )
            ) from exc

    def _batch_with_openai(self, texts: List[str], batch_no: int) -> List[List[float]]:
        preview = _safe_preview(texts[0] if texts else "")
        logger.info(
            "Embedding批量调用: style=openai base=%s model=%s batch_no=%s batch_size=%s input_preview=%s",
            self.embedding_api_base,
            self.model,
            batch_no,
            len(texts),
            preview,
        )
        try:
            response = self._openai_client.embeddings.create(
                model=self.model,
                input=texts,
                timeout=self.timeout,
            )
            data = getattr(response, "data", None) or []
            embeddings: List[List[float]] = []
            for item in data:
                emb = getattr(item, "embedding", None)
                if emb is None and isinstance(item, dict):
                    emb = item.get("embedding")
                if not isinstance(emb, list) or not emb:
                    raise RuntimeError("openai返回了空embedding项")
                embeddings.append(emb)

            if len(embeddings) != len(texts):
                raise RuntimeError(f"openai返回向量数与输入数不一致: expected={len(texts)} actual={len(embeddings)}")

            return embeddings
        except RuntimeError as exc:
            raise RuntimeError(
                self._build_error_message(
                    action="批量生成embedding",
                    style="openai",
                    base_url=self.embedding_api_base,
                    message=str(exc),
                    batch_no=batch_no,
                    preview=preview,
                )
            ) from exc
        except Exception as exc:
            fields = _extract_openai_error_fields(exc)
            raise RuntimeError(
                self._build_error_message(
                    action="批量生成embedding",
                    style="openai",
                    base_url=self.embedding_api_base,
                    status_code=fields.get("status_code"),
                    error_code=fields.get("error_code"),
                    request_id=fields.get("request_id"),
                    message=fields.get("message") or str(exc),
                    batch_no=batch_no,
                    preview=preview,
                )
            ) from exc

    def _generate_with_dashscope(self, text: str, batch_no: Optional[int] = None) -> List[float]:
        preview = _safe_preview(text)
        try:
            response = dashscope.TextEmbedding.call(model=self.model, input=text)
            status_code = getattr(response, "status_code", None)
            if status_code != 200:
                raise RuntimeError(
                    self._build_error_message(
                        action="生成embedding",
                        style="dashscope",
                        base_url=self.dashscope_http_base,
                        status_code=str(status_code) if status_code is not None else None,
                        error_code=str(getattr(response, "code", "") or "") or None,
                        request_id=str(getattr(response, "request_id", "") or "") or None,
                        message=str(getattr(response, "message", "") or "dashscope响应非200"),
                        batch_no=batch_no,
                        preview=preview,
                    )
                )

            embedding = response["output"]["embeddings"][0]["embedding"]
            if not isinstance(embedding, list) or not embedding:
                raise RuntimeError("dashscope返回embedding为空")
            return embedding
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(
                self._build_error_message(
                    action="生成embedding",
                    style="dashscope",
                    base_url=self.dashscope_http_base,
                    message=str(exc),
                    batch_no=batch_no,
                    preview=preview,
                )
            ) from exc

    def _batch_with_dashscope(self, texts: List[str], batch_no: int) -> List[List[float]]:
        preview = _safe_preview(texts[0] if texts else "")
        logger.info(
            "Embedding批量调用: style=dashscope base=%s model=%s batch_no=%s batch_size=%s input_preview=%s",
            self.dashscope_http_base,
            self.model,
            batch_no,
            len(texts),
            preview,
        )
        response = dashscope.TextEmbedding.call(model=self.model, input=texts)
        status_code = getattr(response, "status_code", None)
        if status_code == 200:
            embeddings = [item["embedding"] for item in response["output"]["embeddings"]]
            if len(embeddings) != len(texts):
                raise RuntimeError(
                    self._build_error_message(
                        action="批量生成embedding",
                        style="dashscope",
                        base_url=self.dashscope_http_base,
                        status_code="200",
                        message=f"dashscope返回向量数与输入数不一致: expected={len(texts)} actual={len(embeddings)}",
                        batch_no=batch_no,
                        preview=preview,
                    )
                )
            return embeddings

        error_message = self._build_error_message(
            action="批量生成embedding",
            style="dashscope",
            base_url=self.dashscope_http_base,
            status_code=str(status_code) if status_code is not None else None,
            error_code=str(getattr(response, "code", "") or "") or None,
            request_id=str(getattr(response, "request_id", "") or "") or None,
            message=str(getattr(response, "message", "") or "dashscope响应非200"),
            batch_no=batch_no,
            preview=preview,
        )
        logger.error(error_message)

        # DashScope批量失败时退化到单条调用，以便拿到更具体失败条目
        embeddings: List[List[float]] = []
        for text in texts:
            embeddings.append(self._generate_with_dashscope(text, batch_no=batch_no))
        return embeddings

    def _generate_with_style(self, style: str, text: str, batch_no: Optional[int] = None) -> List[float]:
        if style == "openai":
            return self._generate_with_openai(text, batch_no=batch_no)
        return self._generate_with_dashscope(text, batch_no=batch_no)

    def _batch_with_style(self, style: str, texts: List[str], batch_no: int) -> List[List[float]]:
        if style == "openai":
            return self._batch_with_openai(texts, batch_no=batch_no)
        return self._batch_with_dashscope(texts, batch_no=batch_no)

    def generate_embedding(self, text: str) -> List[float]:
        errors: List[str] = []
        attempts = self._style_attempt_order()

        for index, style in enumerate(attempts):
            try:
                return self._generate_with_style(style, text)
            except Exception as exc:
                errors.append(str(exc))
                if index < len(attempts) - 1:
                    logger.warning(
                        "Embedding调用失败，尝试回退风格: failed_style=%s next_style=%s reason=%s",
                        style,
                        attempts[index + 1],
                        exc,
                    )
                else:
                    logger.error("生成embedding失败: %s", exc)

        raise RuntimeError("embedding调用失败: " + " | ".join(errors))

    def batch_generate_embeddings(self, texts: List[str], batch_size: int = 25) -> List[List[float]]:
        all_embeddings: List[List[float]] = []
        try:
            for i in range(0, len(texts), batch_size):
                batch_no = i // batch_size + 1
                batch_texts = texts[i : i + batch_size]

                errors: List[str] = []
                attempts = self._style_attempt_order()
                for index, style in enumerate(attempts):
                    try:
                        embeddings = self._batch_with_style(style, batch_texts, batch_no=batch_no)
                        all_embeddings.extend(embeddings)
                        logger.info("已处理 %s/%s 条文本", len(all_embeddings), len(texts))
                        break
                    except Exception as exc:
                        errors.append(str(exc))
                        if index < len(attempts) - 1:
                            logger.warning(
                                "Embedding批量调用失败，尝试回退风格: batch_no=%s failed_style=%s next_style=%s reason=%s",
                                batch_no,
                                style,
                                attempts[index + 1],
                                exc,
                            )
                        else:
                            raise RuntimeError(" | ".join(errors)) from exc

            return all_embeddings
        except Exception as exc:
            logger.error("批量生成失败: %s", exc)
            raise

    def get_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        try:
            import numpy as np

            v1 = np.array(embedding1)
            v2 = np.array(embedding2)
            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as exc:
            logger.error("计算相似度失败: %s", exc)
            return 0.0


_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
