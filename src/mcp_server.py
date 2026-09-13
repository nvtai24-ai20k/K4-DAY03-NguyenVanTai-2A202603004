"""
🔌 MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE
Mô phỏng kiến trúc MCP Server (Client-Server Architecture) cung cấp công cụ chuẩn hóa.
"""

import json
import sys
from typing import Dict, Any, List
from tools import TOOLS_SCHEMA, dispatch_tool_call

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class MCPHelpdeskServer:
    """
    Giả lập MCP Server tuân thủ chuẩn giao thức Model Context Protocol
    """
    def __init__(self, server_name: str = "it-helpdesk-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"
        self._request_id = 0

    def list_tools(self) -> List[Dict[str, Any]]:
        """Trả về danh sách các Tools chuẩn giao thức MCP"""
        return TOOLS_SCHEMA

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        [TASK 2.1] Thực thi request gọi Tool theo chuẩn MCP JSON-RPC 2.0
        """
        self._request_id += 1

        # 1. Tool Router thực thi tool và trả về chuỗi JSON
        raw_result = dispatch_tool_call(tool_name, arguments or {})

        # 2. Chuyển chuỗi JSON thành Dictionary
        try:
            content = json.loads(raw_result)
        except (TypeError, json.JSONDecodeError):
            content = {"status": "INVALID_TOOL_OUTPUT", "raw_output": str(raw_result)}

        # 3. Đóng gói phản hồi JSON-RPC 2.0
        return {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "server": self.server_name,
            "tool": tool_name,
            "result": content
        }


if __name__ == "__main__":
    print("==========================================================")
    print("🔌 KIỂM THỬ ĐỘC LẬP MCP SERVER (it-helpdesk-mcp-server)")
    print("==========================================================")

    server = MCPHelpdeskServer()
    tools = server.list_tools()
    print(f"✅ [MCP SERVER] Đã khởi tạo thành công {server.server_name} (Version: {server.version})")
    print(f"📦 Số lượng Tools công bố qua MCP: {len(tools)}")

    # Kiểm tra trạng thái TODO 1.2 (Tool Schema)
    for tool in tools:
        params = tool.get("parameters", {})
        if params.get("properties"):
            print(f"✅ [TODO 1.2]: Tool '{tool['name']}' có schema đầy đủ ({len(params['properties'])} tham số, bắt buộc: {params.get('required', [])}).")
        else:
            print(f"⏳ [TODO 1.2]: Tool '{tool.get('name')}' chưa được định nghĩa properties trong 'src/tools.py'.")

    # Kiểm tra trạng thái TODO 2.1 (call_tool)
    test_result = server.call_tool("helpdesk_query", {"employee_id": "NV001"})
    if not test_result:
        print("⏳ [TODO 2.1]: Hàm call_tool() đang trả về rỗng. Học viên hãy hoàn thiện TODO 2.1 trong 'src/mcp_server.py'!")
    else:
        print(f"✅ [TODO 2.1]: Test dispatch tool 'helpdesk_query' thành công:")
        print(f"   Phản hồi JSON-RPC: {json.dumps(test_result, ensure_ascii=False)}")
