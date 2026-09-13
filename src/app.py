"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối MCP Server (Cấp 3).
Đề tài: Trợ lý Hỗ trợ Kỹ thuật IT Helpdesk.
"""

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from mcp_server import MCPHelpdeskServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider, MockOfflineProvider

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    config_path = os.path.join(BASE_DIR, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(BASE_DIR, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            print("👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list, filename: str = "trace_waterfall.json"):
    """Ghi vết log Waterfall Trace Log ra thư mục docs/"""
    docs_dir = os.path.join(BASE_DIR, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, filename)
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider):
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def run_react_agent(user_query: str, provider, mcp_server: MCPHelpdeskServer,
                    test_case_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server.
    Mỗi Observation được nạp lại cho LLM ở vòng kế tiếp cho tới khi LLM đưa ra Final Answer.
    Trả về danh sách trace log của phiên thực thi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")

    trace_logs = []
    history = []  # Các lượt Action -> Observation đã thực thi, gửi lại cho LLM ở mỗi vòng
    tools_list = mcp_server.list_tools()
    query_start = time.perf_counter()

    def trace_event(step: int, action_type: str, event_start: float, **fields) -> Dict[str, Any]:
        return {
            "test_case_id": test_case_id,
            "step": step,
            "query": user_query,
            "action_type": action_type,
            **fields,
            "provider": provider.__class__.__name__,
            "model": getattr(provider, "model_name", ""),
            "start_offset_ms": round((event_start - query_start) * 1000, 2)
        }

    for step in range(1, MAX_ITERATIONS + 1):
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")
        step_start = time.perf_counter()

        # Thought: gọi LLM với Native Tool Calling Specs + toàn bộ Action/Observation trước đó
        llm_response = provider.generate_with_tools(
            user_query, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT, history=history
        )
        llm_latency_ms = _elapsed_ms(step_start)
        retry_wait_ms = llm_response.get("retry_wait_ms", 0.0)  # Thời gian chờ retry (429/timeout), đã tính trong llm_latency_ms
        thought = llm_response.get("thought") or "Đang suy luận..."
        print(f"🧠 [Thought]: {thought}")
        response_type = llm_response.get("type")

        # Trường hợp 1: LLM đã đủ dữ liệu và trả lời bằng văn bản -> dừng vòng lặp
        if response_type == "text":
            final_content = llm_response.get("content", "")
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append(trace_event(
                step, "FINAL_ANSWER", step_start,
                thought=thought, output=final_content,
                llm_latency_ms=llm_latency_ms, retry_wait_ms=retry_wait_ms, latency_ms=llm_latency_ms
            ))
            return trace_logs

        # Trường hợp 2: LLM đề xuất gọi Tool (Action) -> MCP Server thực thi -> Observation
        if response_type == "tool_call":
            observations = []
            for index, call in enumerate(llm_response["tool_calls"]):
                print(f"🛠️ [Action]: {call['name']}({json.dumps(call['arguments'], ensure_ascii=False)})")
                tool_start = time.perf_counter()
                mcp_response = mcp_server.call_tool(call["name"], call["arguments"])
                tool_latency_ms = _elapsed_ms(tool_start)
                observation = mcp_response.get("result", {})
                print(f"👁️ [Observation từ MCP Server]: {json.dumps(observation, ensure_ascii=False)}")
                observations.append(observation)

                # Nhiều tool call trong cùng một lượt dùng chung một lần gọi LLM (tính vào call đầu tiên)
                call_llm_ms = llm_latency_ms if index == 0 else 0.0
                trace_logs.append(trace_event(
                    step, "TOOL_EXECUTION", step_start if index == 0 else tool_start,
                    thought=thought, tool_name=call["name"], arguments=call["arguments"],
                    mcp_request_id=mcp_response.get("id"), observation=observation,
                    llm_latency_ms=call_llm_ms, retry_wait_ms=retry_wait_ms if index == 0 else 0.0,
                    tool_latency_ms=tool_latency_ms,
                    latency_ms=round(call_llm_ms + tool_latency_ms, 2)
                ))

            history.append({
                "tool_calls": llm_response["tool_calls"],
                "observations": observations,
                "raw": llm_response.get("raw")
            })
            continue

        # Trường hợp 3: Lỗi gọi LLM (hết quota, mất mạng, phản hồi bị chặn...) -> dừng và ghi vết lỗi
        error = llm_response.get("error") or f"Phản hồi không hợp lệ từ LLM: {llm_response}"
        print(f"❌ [LLM Error]: {error}")
        trace_logs.append(trace_event(
            step, "LLM_ERROR", step_start,
            thought=thought, error=error,
            llm_latency_ms=llm_latency_ms, retry_wait_ms=retry_wait_ms, latency_ms=llm_latency_ms
        ))
        return trace_logs

    message = f"Agent dừng sau {MAX_ITERATIONS} vòng lặp mà chưa đưa ra Final Answer."
    print(f"⚠️ [MAX_ITERATIONS]: {message}")
    trace_logs.append(trace_event(MAX_ITERATIONS, "MAX_ITERATIONS_REACHED", time.perf_counter(), output=message, latency_ms=0.0))
    return trace_logs


def evaluate_test_case(test_case: Dict[str, Any], logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """So khớp chuỗi tool đã gọi với expected_tools của test case"""
    tools_called = [e["tool_name"] for e in logs if e["action_type"] == "TOOL_EXECUTION"]
    finished = bool(logs) and logs[-1]["action_type"] == "FINAL_ANSWER"
    expected = test_case.get("expected_tools")
    if expected is None:
        tools_ok = True
    elif not expected:
        tools_ok = not tools_called
    else:
        tools_ok = all(tool in tools_called for tool in expected)
    return {"passed": finished and tools_ok, "finished": finished, "tools_called": tools_called}


if __name__ == "__main__":
    print("==========================================================")
    print("🖥️ AI20K DAY 03 LAB: CHATBOT VS REACT AGENT (IT HELPDESK)")
    print("==========================================================")

    provider = get_llm_provider()
    mcp_server = MCPHelpdeskServer()

    print(f"🔌 LLM Provider: {provider.__class__.__name__} ({getattr(provider, 'model_name', '')})")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")
    if isinstance(provider, MockOfflineProvider):
        print("⚠️ [MOCK OFFLINE MODE]: Chưa có API Key thật trong .env. Kết quả chỉ dùng để debug, không dùng để nộp bài.\n")

    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")

    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với ReAct Agent:")
        print("💡 Gợi ý câu hỏi thử nghiệm:")
        print("   - Câu hỏi chung: 'Làm sao để kết nối VPN công ty khi làm việc ở nhà?'")
        print("   - Tra cứu: 'Tài khoản của nhân viên NV002 đang ở trạng thái gì?'")
        print("   - Tạo ticket: 'Tôi là NV003, màn hình phụ không nhận tín hiệu, tạo giúp tôi yêu cầu hỗ trợ'")
        print("   - Gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.")
        print("   (Trace của phiên này lưu tại docs/trace_session.json, không ghi đè docs/trace_waterfall.json)\n")
        session_traces = []
        while True:
            try:
                user_input = input("👤 Nhân viên hỏi: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt! Kết thúc phiên trò chuyện.")
                    break
                session_traces.extend(run_react_agent(user_input, provider, mcp_server))
                save_waterfall_trace(session_traces, "trace_session.json")
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
    elif "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases:")
        completed_count = 0
        passed_count = 0
        todo_count = 0
        all_traces = []

        for tc in tests:
            print(f"\n==================================================")
            print(f"🧪 [{tc['id']}] Loại test: {tc['type']} (Độ phức tạp: {tc['complexity']})")
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")

            if tc["question"].strip().startswith("TODO"):
                print(f"⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]:")
                print(f"   {tc['question']}")
                print(f"   👉 Hãy mở file 'config/test_cases.json' để viết câu hỏi thực tế cho Test Case này!")
                todo_count += 1
            else:
                logs = run_react_agent(tc["question"], provider, mcp_server, test_case_id=tc["id"])
                all_traces.extend(logs)
                completed_count += 1
                verdict = evaluate_test_case(tc, logs)
                passed_count += verdict["passed"]
                status_icon = "✅ PASS" if verdict["passed"] else "❌ FAIL"
                print(f"\n{status_icon} [{tc['id']}]: Tools đã gọi = {verdict['tools_called'] or 'không gọi tool'} | Kỳ vọng = {tc.get('expected_tools')}")

        tool_events = [e for e in all_traces if e["action_type"] == "TOOL_EXECUTION"]
        tool_success = sum(e["observation"].get("status") == "SUCCESS" for e in tool_events)
        print(f"\n==================================================")
        print(f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi {completed_count}/{len(tests)} Test Cases | PASS {passed_count}/{completed_count} | {todo_count} Test Cases đang chờ điền câu hỏi (TODO)")
        print(f"🛠️ [MCP]: {len(tool_events)} lượt gọi Tool qua MCP Server ({tool_success} SUCCESS, {len(tool_events) - tool_success} trả về trạng thái khác)")
        if all_traces:
            save_waterfall_trace(all_traces)
        print(f"💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'")
    else:
        # Chế độ mặc định khi chỉ gõ 'python src/app.py'
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
        print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")

        sample_query = tests[1]["question"]
        print(f"--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU (TC02: Tra cứu ticket) ---")
        logs = run_react_agent(sample_query, provider, mcp_server, test_case_id=tests[1]["id"])
        save_waterfall_trace(logs, "trace_session.json")
        print("\n💡 Hãy thử ngay lệnh: python src/app.py --interactive để chat trực tiếp!")
