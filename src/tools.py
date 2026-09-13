"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
Đề tài: Trợ lý Hỗ trợ Kỹ thuật IT Helpdesk (Gợi ý 2.2).
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional

TICKET_CATEGORIES = ["NETWORK", "ACCOUNT", "HARDWARE", "SOFTWARE"]
TICKET_PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
ACTIVE_TICKET_STATUSES = ["OPEN", "IN_PROGRESS"]

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    # Tool 1 (Tra cứu thông tin): hồ sơ IT của nhân viên và ticket sự cố
    {
        "name": "helpdesk_query",
        "description": (
            "Tra cứu dữ liệu hệ thống IT Helpdesk. Truyền employee_id để lấy hồ sơ IT của nhân viên "
            "(phòng ban, trạng thái tài khoản, thiết bị, kỹ thuật viên phụ trách) kèm toàn bộ ticket sự cố của nhân viên đó; "
            "hoặc truyền ticket_id để xem chi tiết một ticket. Phải truyền ít nhất một trong hai tham số."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Mã nhân viên cần tra cứu (ví dụ: 'NV001')"
                },
                "ticket_id": {
                    "type": "string",
                    "description": "Mã ticket sự cố cần tra cứu (ví dụ: 'IT-1012')"
                }
            },
            "required": []
        }
    },

    # Tool 2 (Hành động): tạo yêu cầu hỗ trợ kỹ thuật mới
    {
        "name": "create_support_ticket",
        "description": (
            "Tạo ticket yêu cầu hỗ trợ kỹ thuật mới cho một nhân viên. Hệ thống từ chối tạo nếu mã nhân viên không tồn tại "
            "hoặc nhân viên đã có ticket cùng loại sự cố đang ở trạng thái OPEN/IN_PROGRESS."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Mã nhân viên gặp sự cố (ví dụ: 'NV001')"
                },
                "category": {
                    "type": "string",
                    "enum": TICKET_CATEGORIES,
                    "description": (
                        "Loại sự cố: NETWORK (mạng, wifi, VPN), ACCOUNT (tài khoản, mật khẩu, quyền truy cập), "
                        "HARDWARE (máy tính, máy in, thiết bị ngoại vi), SOFTWARE (cài đặt hoặc lỗi phần mềm)"
                    )
                },
                "priority": {
                    "type": "string",
                    "enum": TICKET_PRIORITIES,
                    "description": (
                        "Mức ưu tiên: CRITICAL (ảnh hưởng nhiều người hoặc cả hệ thống), HIGH (nhân viên không thể làm việc), "
                        "MEDIUM (ảnh hưởng một phần công việc), LOW (yêu cầu cài đặt, cải tiến)"
                    )
                },
                "title": {
                    "type": "string",
                    "description": "Tiêu đề ngắn gọn của sự cố (ví dụ: 'Mất kết nối wifi tầng 3 Tòa A')"
                },
                "description": {
                    "type": "string",
                    "description": "Mô tả chi tiết hiện tượng, thời điểm xảy ra và mức độ ảnh hưởng tới công việc"
                },
                "assignee": {
                    "type": "string",
                    "description": "Tên kỹ thuật viên nhận xử lý. Bỏ trống để hệ thống tự giao cho kỹ thuật viên phụ trách của nhân viên"
                }
            },
            "required": ["employee_id", "category", "priority", "title", "description"]
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

EMPLOYEE_DATABASE = {
    "NV001": {
        "full_name": "Nguyễn Minh Khoa",
        "department": "Phòng Kế toán",
        "position": "Chuyên viên kế toán",
        "location": "Tầng 3, Tòa A",
        "email": "khoa.nm@company.vn",
        "account_status": "ACTIVE",
        "device": "Laptop Dell Latitude 5440 (FIN-LT-021)",
        "it_technician": "Trần Quốc Huy"
    },
    "NV002": {
        "full_name": "Lê Thu Hà",
        "department": "Phòng Nhân sự",
        "position": "Chuyên viên tuyển dụng",
        "location": "Tầng 2, Tòa A",
        "email": "ha.lt@company.vn",
        "account_status": "LOCKED",
        "account_note": "Tài khoản bị khóa tự động sau 5 lần nhập sai mật khẩu (08:42 13/09/2026)",
        "device": "Laptop HP EliteBook 840 (HR-LT-007)",
        "it_technician": "Phạm Đức Anh"
    },
    "NV003": {
        "full_name": "Hoàng Gia Bảo",
        "department": "Phòng Kinh doanh",
        "position": "Trưởng phòng",
        "location": "Tầng 5, Tòa B",
        "email": "bao.hg@company.vn",
        "account_status": "ACTIVE",
        "device": "MacBook Pro 14 (SAL-LT-001)",
        "it_technician": "Đỗ Thanh Tùng"
    }
}

TICKET_DATABASE = {
    "IT-1001": {
        "employee_id": "NV001",
        "category": "NETWORK",
        "priority": "MEDIUM",
        "title": "Wifi tầng 3 Tòa A chập chờn",
        "status": "RESOLVED",
        "assignee": "Trần Quốc Huy",
        "created_at": "2026-09-02 09:15",
        "updated_at": "2026-09-05 16:40",
        "resolution": "Đã thay access point AP-A3-02 và kiểm tra kết nối ổn định."
    },
    "IT-1007": {
        "employee_id": "NV001",
        "category": "SOFTWARE",
        "priority": "LOW",
        "title": "Cài add-in Power Query cho Excel",
        "status": "OPEN",
        "assignee": "Trần Quốc Huy",
        "created_at": "2026-09-10 14:05",
        "updated_at": "2026-09-10 14:05"
    },
    "IT-1012": {
        "employee_id": "NV002",
        "category": "ACCOUNT",
        "priority": "HIGH",
        "title": "Tài khoản email và VPN bị khóa",
        "status": "IN_PROGRESS",
        "assignee": "Phạm Đức Anh",
        "created_at": "2026-09-13 08:50",
        "updated_at": "2026-09-13 09:10",
        "note": "Đang chờ quản lý trực tiếp xác minh danh tính trước khi mở khóa."
    }
}

SLA_RESPONSE_TIME = {
    "CRITICAL": "1 giờ",
    "HIGH": "4 giờ làm việc",
    "MEDIUM": "1 ngày làm việc",
    "LOW": "3 ngày làm việc"
}


def _to_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _ticket_view(ticket_id: str) -> Dict[str, Any]:
    return {"ticket_id": ticket_id, **TICKET_DATABASE[ticket_id]}


def execute_helpdesk_query(employee_id: Optional[str] = None, ticket_id: Optional[str] = None) -> str:
    """Thực thi tra cứu hồ sơ IT của nhân viên và/hoặc chi tiết ticket sự cố"""
    employee_id = (employee_id or "").strip().upper()
    ticket_id = (ticket_id or "").strip().upper()
    if not employee_id and not ticket_id:
        return _to_json({
            "status": "INVALID_ARGUMENTS",
            "message": "Cần cung cấp employee_id hoặc ticket_id để tra cứu."
        })

    result: Dict[str, Any] = {"status": "SUCCESS"}

    if ticket_id:
        if ticket_id not in TICKET_DATABASE:
            return _to_json({"status": "NOT_FOUND", "message": f"Không tìm thấy ticket có mã '{ticket_id}'"})
        ticket = _ticket_view(ticket_id)
        owner = EMPLOYEE_DATABASE[ticket["employee_id"]]
        result["ticket"] = ticket
        result["ticket_owner"] = {
            "employee_id": ticket["employee_id"],
            "full_name": owner["full_name"],
            "department": owner["department"]
        }

    if employee_id:
        employee = EMPLOYEE_DATABASE.get(employee_id)
        if not employee:
            return _to_json({
                "status": "NOT_FOUND",
                "message": f"Không tìm thấy nhân viên có mã '{employee_id}' trong hệ thống IT Helpdesk"
            })
        tickets = [_ticket_view(tid) for tid, t in TICKET_DATABASE.items() if t["employee_id"] == employee_id]
        result["employee_id"] = employee_id
        result["employee"] = employee
        result["tickets"] = tickets
        result["active_ticket_count"] = sum(t["status"] in ACTIVE_TICKET_STATUSES for t in tickets)

    return _to_json(result)


def execute_create_support_ticket(employee_id: str, category: str, priority: str, title: str,
                                  description: str = "", assignee: Optional[str] = None) -> str:
    """Thực thi tạo ticket yêu cầu hỗ trợ kỹ thuật"""
    employee_id = employee_id.strip().upper()
    category = category.strip().upper()
    priority = priority.strip().upper()

    employee = EMPLOYEE_DATABASE.get(employee_id)
    if not employee:
        return _to_json({
            "status": "NOT_FOUND",
            "message": f"Không thể tạo ticket: không tìm thấy nhân viên có mã '{employee_id}'"
        })
    if category not in TICKET_CATEGORIES or priority not in TICKET_PRIORITIES:
        return _to_json({
            "status": "INVALID_ARGUMENTS",
            "message": f"category phải thuộc {TICKET_CATEGORIES}, priority phải thuộc {TICKET_PRIORITIES}"
        })

    duplicate_id = next(
        (tid for tid, t in TICKET_DATABASE.items()
         if t["employee_id"] == employee_id and t["category"] == category and t["status"] in ACTIVE_TICKET_STATUSES),
        None
    )
    if duplicate_id:
        return _to_json({
            "status": "DUPLICATE",
            "message": f"Nhân viên {employee_id} đã có ticket {category} đang xử lý ({duplicate_id}), không tạo ticket trùng.",
            "existing_ticket": _ticket_view(duplicate_id)
        })

    ticket_id = f"IT-{max(int(tid.split('-')[1]) for tid in TICKET_DATABASE) + 1}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    TICKET_DATABASE[ticket_id] = {
        "employee_id": employee_id,
        "category": category,
        "priority": priority,
        "title": title.strip(),
        "description": description.strip(),
        "status": "OPEN",
        "assignee": (assignee or "").strip() or employee["it_technician"],
        "created_at": now,
        "updated_at": now
    }
    ticket = _ticket_view(ticket_id)
    return _to_json({
        "status": "SUCCESS",
        "ticket": ticket,
        "sla_response_time": SLA_RESPONSE_TIME[priority],
        "message": (
            f"Đã tạo ticket {ticket_id} ({category}, {priority}) cho {employee['full_name']}, "
            f"giao cho kỹ thuật viên {ticket['assignee']}."
        )
    })


# Router gọi tool thực tế
TOOL_ROUTER = {
    "helpdesk_query": execute_helpdesk_query,
    "create_support_ticket": execute_create_support_ticket
}

def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**(arguments or {}))
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)
