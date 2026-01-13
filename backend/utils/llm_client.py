"""
大模型调用封装
统一封装阿里云大模型API调用，支持重试、错误处理
"""
import time
import logging
from typing import Dict, List, Optional, Any
from openai import OpenAI
from backend.config.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    """大模型客户端类"""

    def __init__(self):
        """初始化大模型客户端"""
        self.api_key = settings.DASHSCOPE_API_KEY
        self.base_url = settings.DASHSCOPE_API_BASE
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.timeout = settings.LLM_TIMEOUT

        # 初始化OpenAI客户端（兼容阿里云DashScope）
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        logger.info(f"LLM客户端初始化完成，模型: {self.model}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        retry_times: int = 3
    ) -> str:
        """
        发起对话请求

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数（可选）
            max_tokens: 最大token数（可选）
            retry_times: 重试次数

        Returns:
            str: 模型返回的文本内容

        Raises:
            Exception: 调用失败且重试后仍失败
        """
        temperature = temperature or self.temperature
        max_tokens = max_tokens or self.max_tokens

        for attempt in range(retry_times):
            try:
                logger.info(f"LLM请求尝试 {attempt + 1}/{retry_times}")

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self.timeout
                )

                result = response.choices[0].message.content
                logger.info(f"LLM请求成功，返回token数: {response.usage.total_tokens}")

                return result

            except Exception as e:
                logger.warning(f"LLM请求失败（第{attempt + 1}次）: {str(e)}")

                if attempt < retry_times - 1:
                    # 指数退避重试
                    wait_time = 2 ** attempt
                    logger.info(f"等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"LLM请求失败，已重试{retry_times}次")
                    raise

    def chat_with_system_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        使用系统提示词对话

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数（可选）
            max_tokens: 最大token数（可选）

        Returns:
            str: 模型返回的文本内容
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self.chat(messages, temperature, max_tokens)

    def extract_json(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取JSON内容

        Args:
            text: 包含JSON的文本

        Returns:
            Dict: 解析后的JSON对象
        """
        import json
        import re

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取JSON代码块
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)

        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass

        # 尝试提取花括号内容
        brace_pattern = r'\{.*\}'
        matches = re.findall(brace_pattern, text, re.DOTALL)

        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法从文本中提取有效的JSON: {text[:200]}...")


# 全局LLM客户端实例
llm_client = LLMClient()
