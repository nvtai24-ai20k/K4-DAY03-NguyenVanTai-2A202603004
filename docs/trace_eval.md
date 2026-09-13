# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Nguyễn Văn Tài  
> **Mã Sinh Viên / Mã Học viên:** 2A202603004  
> **Chủ đề Lựa chọn:** Gợi ý 2.2 — Trợ lý Hỗ trợ Kỹ thuật IT Helpdesk (tra cứu ticket sự cố mạng, tài khoản và tạo yêu cầu hỗ trợ kỹ thuật)  

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 4 / 5 | Yêu cầu điển hình của nhân viên ("wifi lại mất, kiểm tra ticket cũ, chưa có thì tạo mới và giao cho kỹ thuật viên của tôi") phải tách thành chuỗi: tra cứu hồ sơ và ticket → đánh giá ticket cùng loại → xác định mức ưu tiên → tạo ticket → xác nhận mã ticket và SLA. Không chấm 5 vì phần lớn yêu cầu hoàn tất trong 2–3 bước, chưa cần lập kế hoạch dài. |
| **2. Tool Interaction** | 5 / 5 | Trạng thái ticket, trạng thái tài khoản (ACTIVE/LOCKED), thiết bị và kỹ thuật viên phụ trách chỉ có trong hệ thống ITSM, LLM không thể tự biết. Việc tạo ticket là hành động ghi dữ liệu thật, bắt buộc phải đi qua Tool (`helpdesk_query`, `create_support_ticket`) do MCP Server cung cấp. |
| **3. Dynamic Decision** | 4 / 5 | Bước sau phụ thuộc trực tiếp vào Observation: ticket cùng loại đang OPEN/IN_PROGRESS → không tạo trùng; ticket cũ đã RESOLVED → tạo mới; mã nhân viên NOT_FOUND → dừng, không tạo ticket; kỹ thuật viên nhận việc lấy từ hồ sơ trả về. Các nhánh quyết định còn tương đối ít nên chấm 4. |
| **4. Long Horizon Goal** | 3 / 5 | Agent phải giữ mục tiêu ban đầu ("xử lý được sự cố cho nhân viên") xuyên suốt nhiều vòng ReAct trong một phiên. Tuy nhiên chưa cần theo dõi ticket qua nhiều ngày hay ghi nhớ dài hạn giữa các phiên (thuộc Cấp 4). |
| **TỔNG ĐIỂM AGENTIC FIT** | **16 / 20** | *Tổng điểm > 12/20: bài toán rất phù hợp triển khai Agentic System (ReAct Agent + MCP).* |

### Tool Specs công bố qua MCP Server (`it-helpdesk-mcp-server`)

| Tool | Loại | Tham số (JSON Schema) | Kết quả trả về |
| :--- | :--- | :--- | :--- |
| `helpdesk_query` | Tra cứu | `employee_id` (string), `ticket_id` (string) — truyền ít nhất một | `SUCCESS` kèm hồ sơ nhân viên + danh sách ticket, hoặc chi tiết ticket; `NOT_FOUND`; `INVALID_ARGUMENTS` |
| `create_support_ticket` | Hành động | **bắt buộc:** `employee_id`, `category` (enum NETWORK/ACCOUNT/HARDWARE/SOFTWARE), `priority` (enum LOW/MEDIUM/HIGH/CRITICAL), `title`, `description`; **tùy chọn:** `assignee` | `SUCCESS` kèm ticket mới + SLA; `NOT_FOUND`; `DUPLICATE` (đã có ticket cùng loại đang xử lý); `INVALID_ARGUMENTS` |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ✅ Chạy `python src/app.py --all` với `LLM_PROVIDER=gemini`, model **`gemini-3.6-flash`** (Google Gemini API thật, Native Tool Calling). Mọi sự kiện trong `docs/trace_waterfall.json` đều ghi `"provider": "GeminiProvider"`. Trường `thought` là thought summary do Gemini trả về (`include_thoughts=True`).

### 2.1. Waterfall tổng hợp 11 sự kiện

| TC | Step | action_type | Tool / Arguments | Observation | start_offset_ms | latency_ms |
| :---: | :---: | :--- | :--- | :--- | ---: | ---: |
| TC01 | 1 | FINAL_ANSWER | — (không gọi tool) | — | 0.00 | 7 147.81 |
| TC02 | 1 | TOOL_EXECUTION | `helpdesk_query(ticket_id=IT-1012)` | SUCCESS (IN_PROGRESS, Phạm Đức Anh) | 0.00 | 2 722.01 |
| TC02 | 2 | FINAL_ANSWER | — | — | 2 722.07 | 3 949.13 |
| TC03 | 1 | TOOL_EXECUTION | `helpdesk_query(employee_id=NV003)` | SUCCESS (0 ticket đang mở) | 0.00 | 3 630.26 |
| TC03 | 2 | TOOL_EXECUTION | `create_support_ticket(NV003, HARDWARE, MEDIUM)` | SUCCESS → **IT-1013** | 3 630.33 | 4 534.77 |
| TC03 | 3 | FINAL_ANSWER | — | — | 8 165.15 | 3 644.02 |
| TC04 | 1 | TOOL_EXECUTION | `helpdesk_query(employee_id=NV001)` | SUCCESS (IT-1001 NETWORK đã RESOLVED) | 0.00 | 37 667.38 * |
| TC04 | 2 | TOOL_EXECUTION | `create_support_ticket(NV001, NETWORK, HIGH, Trần Quốc Huy)` | SUCCESS → **IT-1014** | 37 667.46 | 5 389.61 |
| TC04 | 3 | FINAL_ANSWER | — | — | 43 057.17 | 5 303.39 |
| TC05 | 1 | TOOL_EXECUTION | `helpdesk_query(employee_id=NV999)` | **NOT_FOUND** | 0.00 | 4 804.69 |
| TC05 | 2 | FINAL_ANSWER | — (dừng, không tạo ticket) | — | 4 804.74 | 3 639.48 |

\* Gồm `retry_wait_ms = 33 000` do Gemini free tier trả lỗi 429 (rate limit) và agent tự retry; thời gian gọi LLM thực tế ≈ 4 667 ms. Thời gian thực thi tool trên MCP Server (`tool_latency_ms`) đều < 0.1 ms, độ trễ chủ yếu nằm ở lượt gọi LLM.

### 2.2. Trích xuất tiêu biểu — TC04 (Multi-step ReAct: Tra cứu → Quyết định → Tạo ticket → Final Answer)

Trích nguyên văn từ `docs/trace_waterfall.json`; riêng trường `thought` được rút gọn (đánh dấu `[...]`) vì bản gốc dài.

```json
[
  {
    "test_case_id": "TC04",
    "step": 1,
    "query": "Tôi là NV001, wifi ở tầng 3 lại mất kết nối hoàn toàn nên tôi không làm việc được. Kiểm tra xem tôi còn ticket mạng nào đang mở không; nếu không có thì tạo ticket mới và giao cho kỹ thuật viên phụ trách của tôi.",
    "action_type": "TOOL_EXECUTION",
    "thought": "**Analyzing a Network Connectivity Issue for NV001** [...] Following my established ReAct process and Rule 4, the first step is to check if NV001 already has an open or in-progress network-related ticket. [...] I'm going to use `helpdesk_query` with `employee_id: \"NV001\"`. [...]",
    "tool_name": "helpdesk_query",
    "arguments": { "employee_id": "NV001" },
    "mcp_request_id": 4,
    "observation": {
      "status": "SUCCESS",
      "employee_id": "NV001",
      "employee": {
        "full_name": "Nguyễn Minh Khoa",
        "department": "Phòng Kế toán",
        "position": "Chuyên viên kế toán",
        "location": "Tầng 3, Tòa A",
        "email": "khoa.nm@company.vn",
        "account_status": "ACTIVE",
        "device": "Laptop Dell Latitude 5440 (FIN-LT-021)",
        "it_technician": "Trần Quốc Huy"
      },
      "tickets": [
        {
          "ticket_id": "IT-1001", "employee_id": "NV001", "category": "NETWORK", "priority": "MEDIUM",
          "title": "Wifi tầng 3 Tòa A chập chờn", "status": "RESOLVED", "assignee": "Trần Quốc Huy",
          "created_at": "2026-09-02 09:15", "updated_at": "2026-09-05 16:40",
          "resolution": "Đã thay access point AP-A3-02 và kiểm tra kết nối ổn định."
        },
        {
          "ticket_id": "IT-1007", "employee_id": "NV001", "category": "SOFTWARE", "priority": "LOW",
          "title": "Cài add-in Power Query cho Excel", "status": "OPEN", "assignee": "Trần Quốc Huy",
          "created_at": "2026-09-10 14:05", "updated_at": "2026-09-10 14:05"
        }
      ],
      "active_ticket_count": 1
    },
    "llm_latency_ms": 37667.3,
    "retry_wait_ms": 33000.0,
    "tool_latency_ms": 0.08,
    "latency_ms": 37667.38,
    "provider": "GeminiProvider",
    "model": "gemini-3.6-flash",
    "start_offset_ms": 0.0
  },
  {
    "test_case_id": "TC04",
    "step": 2,
    "action_type": "TOOL_EXECUTION",
    "thought": "**My Analysis of the Support Ticket Data** [...] I see two tickets associated with NV001: IT-1001, which was a NETWORK issue and has been RESOLVED, and IT-1007, a SOFTWARE issue that's currently OPEN. The key takeaway here is there are *no* open or in-progress NETWORK tickets for this employee right now. [...] `priority`: HIGH – the user explicitly stated they're experiencing a complete loss of connection, preventing them from working. [...] `assignee`: Trần Quốc Huy [...]",
    "tool_name": "create_support_ticket",
    "arguments": {
      "description": "Mất kết nối wifi tầng 3 Tòa A hoàn toàn, nhân viên không thể làm việc.",
      "employee_id": "NV001",
      "title": "Mất kết nối wifi tầng 3 Tòa A",
      "category": "NETWORK",
      "priority": "HIGH",
      "assignee": "Trần Quốc Huy"
    },
    "mcp_request_id": 5,
    "observation": {
      "status": "SUCCESS",
      "ticket": {
        "ticket_id": "IT-1014", "employee_id": "NV001", "category": "NETWORK", "priority": "HIGH",
        "title": "Mất kết nối wifi tầng 3 Tòa A",
        "description": "Mất kết nối wifi tầng 3 Tòa A hoàn toàn, nhân viên không thể làm việc.",
        "status": "OPEN", "assignee": "Trần Quốc Huy",
        "created_at": "2026-09-13 10:12", "updated_at": "2026-09-13 10:12"
      },
      "sla_response_time": "4 giờ làm việc",
      "message": "Đã tạo ticket IT-1014 (NETWORK, HIGH) cho Nguyễn Minh Khoa, giao cho kỹ thuật viên Trần Quốc Huy."
    },
    "llm_latency_ms": 5389.52,
    "retry_wait_ms": 0.0,
    "tool_latency_ms": 0.09,
    "latency_ms": 5389.61,
    "provider": "GeminiProvider",
    "model": "gemini-3.6-flash",
    "start_offset_ms": 37667.46
  },
  {
    "test_case_id": "TC04",
    "step": 3,
    "action_type": "FINAL_ANSWER",
    "thought": "**My Analysis of the New Ticket & Context** [...] IT-1014 [...] NETWORK [...] HIGH [...] Trần Quốc Huy [...] 4 giờ làm việc (4 working hours) SLA [...]",
    "output": "Chào anh/chị **Nguyễn Minh Khoa (NV001)**,\n\nTôi đã kiểm tra hệ thống và xác nhận hiện tại anh/chị **không có ticket mạng nào đang mở** (ticket sự cố wifi trước đó `IT-1001` đã được hoàn thành xử lý).\n\nDo đó, tôi đã tạo ticket hỗ trợ mới cho anh/chị với thông tin chi tiết như sau:\n\n- **Mã ticket:** `IT-1014`\n- **Tiêu đề:** Mất kết nối wifi tầng 3 Tòa A\n- **Loại sự cố:** NETWORK\n- **Mức ưu tiên:** HIGH (Do ảnh hưởng trực tiếp đến công việc)\n- **Trạng thái:** OPEN\n- **Kỹ thuật viên xử lý:** Trần Quốc Huy (Kỹ thuật viên phụ trách)\n- **Thời gian phản hồi SLA:** 4 giờ làm việc\n\nKỹ thuật viên phụ trách sẽ nhanh chóng liên hệ và hỗ trợ anh/chị xử lý sự cố này.",
    "llm_latency_ms": 5303.39,
    "retry_wait_ms": 0.0,
    "latency_ms": 5303.39,
    "provider": "GeminiProvider",
    "model": "gemini-3.6-flash",
    "start_offset_ms": 43057.17
  }
]
```

**Nhận xét:** Observation ở Step 1 quyết định trực tiếp Action ở Step 2. Agent đọc được ticket NETWORK cũ `IT-1001` đã `RESOLVED` nên cho phép tạo mới, lấy `it_technician` từ hồ sơ để gán `assignee`, và tự suy ra `priority = HIGH` từ mô tả "không làm việc được". Final Answer chỉ dùng dữ liệu có trong Observation (mã `IT-1014`, SLA 4 giờ), không bịa thông tin.

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini/OpenAI).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** 6 lượt (5 `SUCCESS` + 1 `NOT_FOUND` đúng kỳ vọng ở TC05; không có lượt gọi sai tool, sai tham số hay tạo ticket trùng).
- **Kết quả đẩy Repo nộp bài:** [ ] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

| TC | Loại | Kỳ vọng | Chuỗi tool thực tế | Kết quả |
| :---: | :--- | :--- | :--- | :---: |
| TC01 | direct_query | Trả lời trực tiếp, không gọi tool | (không gọi tool) | ✅ PASS |
| TC02 | single_tool_query | Tra cứu ticket IT-1012 | `helpdesk_query` | ✅ PASS |
| TC03 | ticket_creation | Tạo ticket HARDWARE/MEDIUM cho NV003 | `helpdesk_query` → `create_support_ticket` (IT-1013) | ✅ PASS |
| TC04 | multi_step_reasoning | Tra cứu → không có ticket NETWORK mở → tạo ticket HIGH giao cho KTV phụ trách | `helpdesk_query` → `create_support_ticket` (IT-1014) | ✅ PASS |
| TC05 | edge_case_handling | NV999 NOT_FOUND → không tạo ticket, không bịa dữ liệu | `helpdesk_query` (NOT_FOUND) → dừng | ✅ PASS |

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
