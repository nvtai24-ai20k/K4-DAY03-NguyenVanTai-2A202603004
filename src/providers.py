"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling nhiều lượt và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.

Giao ước chung của generate_with_tools():
- history: các lượt Action -> Observation đã thực thi trong vòng ReAct, mỗi phần tử có dạng
    {"tool_calls": [{"id", "name", "arguments"}], "observations": [dict, ...], "raw": <message gốc của provider>}
- Giá trị trả về là một trong ba dạng:
    {"type": "text", "content": str, "thought": str}
    {"type": "tool_call", "tool_calls": [{"id", "name", "arguments"}], "thought": str, "raw": Any}
    {"type": "error", "error": str, "thought": str}
"""

import os
import re
import sys
import json
import time
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

RETRYABLE_STATUS_CODES = (429, 500, 503)


def _is_placeholder_key(key: Optional[str]) -> bool:
    return not key or key.startswith("your_")


def _is_transient_error(error: Exception) -> bool:
    """Lỗi tạm thời đáng thử lại: 429/5xx từ API hoặc lỗi mạng (timeout, mất kết nối)"""
    code = getattr(error, "code", None)
    if isinstance(code, int):
        return code in RETRYABLE_STATUS_CODES
    return isinstance(error, (ConnectionError, TimeoutError)) or any(
        cls.__name__ in ("TransportError", "TimeoutException") for cls in type(error).__mro__
    )


def _describe_tool_calls(tool_calls: List[Dict[str, Any]]) -> str:
    return ", ".join(f"{c['name']}({json.dumps(c['arguments'], ensure_ascii=False)})" for c in tool_calls)


class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    model_name = ""

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "",
                            history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key (nhận diện intent bằng từ khóa)"""
    CATEGORY_KEYWORDS = [
        ("NETWORK", ["wifi", "mạng", "vpn", "internet", "kết nối"]),
        ("ACCOUNT", ["tài khoản", "mật khẩu", "khóa", "đăng nhập"]),
        ("HARDWARE", ["máy in", "màn hình", "chuột", "bàn phím", "laptop", "máy tính"]),
    ]

    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"[Mock Chatbot Response]: Xin chào! Tôi đã nhận được câu hỏi '{prompt}'. (Chế độ Chatbot không có Tool tra cứu dữ liệu thời gian thực)."

    @staticmethod
    def _tool_call(name: str, arguments: Dict[str, Any], thought: str) -> Dict[str, Any]:
        return {
            "type": "tool_call",
            "tool_calls": [{"id": f"mock_{name}", "name": name, "arguments": arguments}],
            "thought": thought,
            "raw": None
        }

    @staticmethod
    def _text(content: str, thought: str) -> Dict[str, Any]:
        return {"type": "text", "content": f"[Mock Agent Response]: {content}", "thought": thought}

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "",
                            history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        history = history or []
        text = prompt.lower()
        employee_match = re.search(r"\bnv\d+\b", text)
        ticket_match = re.search(r"\bit-\d+\b", text)
        employee_id = employee_match.group(0).upper() if employee_match else None
        ticket_id = ticket_match.group(0).upper() if ticket_match else None
        wants_new_ticket = "tạo" in text or "yêu cầu hỗ trợ" in text

        # Lượt đầu: quyết định có cần tra cứu hay không
        if not history:
            if ticket_id:
                return self._tool_call("helpdesk_query", {"ticket_id": ticket_id},
                                       f"Người dùng hỏi về ticket {ticket_id}, cần tra cứu trạng thái qua helpdesk_query.")
            if employee_id:
                return self._tool_call("helpdesk_query", {"employee_id": employee_id},
                                       f"Cần tra cứu hồ sơ và ticket hiện có của {employee_id} trước khi quyết định.")
            return self._text(
                "Mật khẩu mạnh cần tối thiểu 12 ký tự gồm chữ hoa, chữ thường, số và ký tự đặc biệt; nên đổi định kỳ 90 ngày và không dùng lại mật khẩu cũ.",
                "Câu hỏi kiến thức IT chung, trả lời trực tiếp không cần gọi Tool."
            )

        # Các lượt sau: đọc Observation gần nhất để quyết định bước tiếp theo
        last_call = history[-1]["tool_calls"][-1]
        last_obs = history[-1]["observations"][-1]
        if last_obs.get("status") != "SUCCESS":
            return self._text(
                f"{last_obs.get('message', 'Không thể xử lý yêu cầu.')} Không có ticket nào được tạo, vui lòng kiểm tra lại thông tin.",
                f"Tool trả về {last_obs.get('status')}, dừng các hành động phụ thuộc."
            )
        if last_call["name"] == "create_support_ticket":
            return self._text(f"{last_obs['message']} Thời gian phản hồi dự kiến: {last_obs.get('sla_response_time')}.",
                              "Ticket đã được tạo thành công, tổng hợp kết quả cho người dùng.")
        if wants_new_ticket and employee_id and "employee" in last_obs:
            category = next((c for c, kws in self.CATEGORY_KEYWORDS if any(k in text for k in kws)), "SOFTWARE")
            active = [t for t in last_obs["tickets"] if t["category"] == category and t["status"] in ("OPEN", "IN_PROGRESS")]
            if active:
                return self._text(f"Bạn đã có ticket {active[0]['ticket_id']} ({category}) đang ở trạng thái {active[0]['status']}, không tạo ticket trùng.",
                                  "Đã có ticket cùng loại đang xử lý, không tạo mới.")
            explicit_priority = next((p for p in ("critical", "high", "medium", "low") if p in text), None)
            priority = explicit_priority.upper() if explicit_priority else ("HIGH" if "mất" in text else "MEDIUM")
            technician = last_obs["employee"]["it_technician"]
            return self._tool_call(
                "create_support_ticket",
                {"employee_id": employee_id, "category": category, "priority": priority,
                 "title": prompt[:60], "description": prompt, "assignee": technician},
                f"{employee_id} không có ticket {category} đang mở, tạo ticket mới giao cho {technician}."
            )
        return self._text(f"Kết quả tra cứu: {json.dumps(last_obs, ensure_ascii=False)}",
                          "Đã có dữ liệu từ MCP Server, tổng hợp kết quả tra cứu.")


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    MAX_ATTEMPTS = 4

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-3.6-flash"
        self.retry_wait_ms = 0.0
        self._client = None

    def _supports_thinking(self) -> bool:
        return not re.match(r"gemini-(1\.|2\.0)", self.model_name)

    @staticmethod
    def _retry_delay_seconds(error, attempt: int) -> float:
        """Ưu tiên retryDelay do API gợi ý (lỗi 429), nếu không có thì backoff lũy thừa"""
        details = getattr(error, "details", None)
        if isinstance(details, dict):
            for item in details.get("error", {}).get("details", []) or []:
                delay = item.get("retryDelay") if isinstance(item, dict) else None
                if delay:
                    try:
                        return min(float(delay.rstrip("s")) + 1, 60)
                    except ValueError:
                        pass
        return min(5 * 2 ** (attempt - 1), 60)

    def _generate_content(self, contents, config=None):
        from google import genai

        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                return self._client.models.generate_content(model=self.model_name, contents=contents, config=config)
            except Exception as e:
                if not _is_transient_error(e) or attempt == self.MAX_ATTEMPTS:
                    raise
                wait_s = self._retry_delay_seconds(e, attempt)
                reason = f"Lỗi {e.code}" if isinstance(getattr(e, "code", None), int) else type(e).__name__
                print(f"⏳ [Gemini API]: {reason}, thử lại sau {wait_s:.0f}s (lần {attempt}/{self.MAX_ATTEMPTS - 1})...")
                time.sleep(wait_s)
                self.retry_wait_ms += wait_s * 1000

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if _is_placeholder_key(self.api_key):
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google.genai import types
            config = types.GenerateContentConfig(system_instruction=system_prompt or None)
            return self._generate_content(prompt, config).text or ""
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "",
                            history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if _is_placeholder_key(self.api_key):
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, history)

        self.retry_wait_ms = 0.0
        result = self._generate_with_tools(prompt, tools_schema, system_prompt, history)
        result["retry_wait_ms"] = round(self.retry_wait_ms, 2)
        return result

    def _generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str,
                             history: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        try:
            from google.genai import types

            # Chuẩn hóa function declarations cho Gemini SDK (bỏ qua schema chưa hoàn chỉnh)
            function_declarations = [
                {"name": t["name"], "description": t.get("description", ""), "parameters": t["parameters"]}
                for t in tools_schema if t.get("name") and t.get("parameters")
            ]

            # Dựng lại hội thoại: câu hỏi -> (lượt gọi tool gốc của model -> Observation) x N
            contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
            for turn in history or []:
                contents.append(turn["raw"])  # Giữ nguyên Content gốc của model (kèm thought_signature)
                contents.append(types.Content(role="user", parts=[
                    types.Part.from_function_response(name=call["name"], response=obs)
                    for call, obs in zip(turn["tool_calls"], turn["observations"])
                ]))

            config = types.GenerateContentConfig(
                system_instruction=system_prompt or None,
                tools=[types.Tool(function_declarations=function_declarations)] if function_declarations else None,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                thinking_config=types.ThinkingConfig(include_thoughts=True) if self._supports_thinking() else None
            )
            response = self._generate_content(contents, config)

            candidate = response.candidates[0] if response.candidates else None
            parts = (candidate.content.parts or []) if candidate and candidate.content else []
            thoughts = [p.text.strip() for p in parts if p.text and p.thought]
            texts = [p.text.strip() for p in parts if p.text and not p.thought]
            calls = [p.function_call for p in parts if p.function_call]

            if calls:
                tool_calls = [
                    {
                        "id": fc.id or f"call_{len(history or [])}_{i}",
                        "name": fc.name,
                        "arguments": json.loads(json.dumps(dict(fc.args or {}), ensure_ascii=False, default=str))
                    }
                    for i, fc in enumerate(calls)
                ]
                return {
                    "type": "tool_call",
                    "tool_calls": tool_calls,
                    "thought": "\n".join(thoughts + texts) or f"Gemini quyết định gọi công cụ: {_describe_tool_calls(tool_calls)}",
                    "raw": candidate.content
                }
            if texts:
                return {
                    "type": "text",
                    "content": "\n".join(texts),
                    "thought": "\n".join(thoughts) or "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
            reason = candidate.finish_reason if candidate else getattr(response, "prompt_feedback", None)
            return {"type": "error", "error": f"Gemini không trả về nội dung (lý do: {reason})", "thought": "\n".join(thoughts)}

        except Exception as e:
            return {"type": "error", "error": f"{type(e).__name__}: {e}", "thought": "Không gọi được Gemini API."}


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4.1-mini"
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if _is_placeholder_key(self.api_key):
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = self._get_client().chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "",
                            history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if _is_placeholder_key(self.api_key):
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, history)

        try:
            tools = [
                {
                    "type": "function",
                    "function": {"name": t["name"], "description": t.get("description", ""), "parameters": t.get("parameters", {})}
                }
                for t in tools_schema if t.get("name")
            ]

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            for turn in history or []:
                messages.append({
                    "role": "assistant",
                    "content": turn.get("raw"),
                    "tool_calls": [
                        {"id": c["id"], "type": "function",
                         "function": {"name": c["name"], "arguments": json.dumps(c["arguments"], ensure_ascii=False)}}
                        for c in turn["tool_calls"]
                    ]
                })
                for call, obs in zip(turn["tool_calls"], turn["observations"]):
                    messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(obs, ensure_ascii=False)})

            request = {"model": self.model_name, "messages": messages}
            if tools:
                # Gọi tuần tự từng tool để mỗi Action dựa trên Observation của bước trước
                request.update(tools=tools, tool_choice="auto", parallel_tool_calls=False)
            msg = self._get_client().chat.completions.create(**request).choices[0].message

            if msg.tool_calls:
                tool_calls = []
                for call in msg.tool_calls:
                    try:
                        args = json.loads(call.function.arguments) if call.function.arguments else {}
                    except json.JSONDecodeError:
                        args = {}
                    tool_calls.append({"id": call.id, "name": call.function.name, "arguments": args})
                return {
                    "type": "tool_call",
                    "tool_calls": tool_calls,
                    "thought": re.sub(r"^\s*thought\s*:\s*", "", msg.content or "", flags=re.IGNORECASE)
                               or f"OpenAI quyết định gọi công cụ: {_describe_tool_calls(tool_calls)}",
                    "raw": msg.content
                }
            return {
                "type": "text",
                "content": msg.content or "",
                "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
            }
        except Exception as e:
            return {"type": "error", "error": f"{type(e).__name__}: {e}", "thought": "Không gọi được OpenAI API."}


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider_type == "gemini" and not _is_placeholder_key(os.getenv("GEMINI_API_KEY")):
        return GeminiProvider()
    if provider_type == "openai" and not _is_placeholder_key(os.getenv("OPENAI_API_KEY")):
        return OpenAIProvider()
    return MockOfflineProvider()
