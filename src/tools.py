"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND (QC ASSISTANT)
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
"""

import json
from typing import Dict, Any

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA
# ==============================================================================

TOOLS_SCHEMA = [
    # Tool 1: Tra cứu ca lỗi kiểm định của Annotator
    {
        "name": "query_qc_error",
        "description": "Tra cứu hồ sơ ca lỗi kiểm định dữ liệu gán nhãn 2D/3D của Annotator theo mã annotator_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "annotator_id": {
                    "type": "string",
                    "description": "Mã định danh của Annotator (ví dụ: 'AN2026001')"
                }
            },
            "required": ["annotator_id"]
        }
    },
    
    # Tool 2: Tạo phiếu yêu cầu Rework
    {
        "name": "create_rework_ticket",
        "description": "Tạo phiếu yêu cầu Rework (sửa lỗi gán nhãn 2D/3D) cho Annotator.",
        "parameters": {
            "type": "object",
            "properties": {
                "annotator_id": {
                    "type": "string",
                    "description": "Mã Annotator cần rework (ví dụ: 'AN2026001')"
                },
                "reason": {
                    "type": "string",
                    "description": "Lý do reject hoặc mô tả lỗi chi tiết (ví dụ: 'Lỗi lệch Bounding Box 3D quá 5cm')"
                },
                "deadline": {
                    "type": "string",
                    "description": "Hạn chót hoàn thành Rework (ví dụ: '2026-09-20' hoặc '14:00 25/09/2026')"
                }
            },
            "required": ["annotator_id", "reason", "deadline"]
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

MOCK_DATABASE = {
    "AN2026001": {
        "annotator_name": "Nguyễn Văn An",
        "project": "Autonomous Driving 3D Point Cloud",
        "total_frames_checked": 150,
        "rejected_frames": ["Frame_0042", "Frame_0089", "Frame_0105"],
        "error_type": "Lỗi lệch Bounding Box 3D & Thiếu nhãn LiDAR",
        "qc_status": "REJECTED_NEEDS_REWORK",
        "reviewer": "QC Lead Minh"
    },
    "AN2026002": {
        "annotator_name": "Trần Thị Bình",
        "project": "2D Image Object Detection",
        "total_frames_checked": 300,
        "rejected_frames": ["Frame_0012"],
        "error_type": "Sai Class nhãn Pedestrian",
        "qc_status": "REJECTED_NEEDS_REWORK",
        "reviewer": "QC Lead Lan"
    }
}


def execute_query_qc_error(annotator_id: str) -> str:
    """Thực thi tra cứu hồ sơ ca lỗi kiểm định theo mã Annotator"""
    annotator = MOCK_DATABASE.get(annotator_id.strip().upper())
    if annotator:
        return json.dumps({
            "status": "SUCCESS",
            "annotator_id": annotator_id,
            "data": annotator
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy dữ liệu ca lỗi cho Annotator có mã '{annotator_id}'"
        }, ensure_ascii=False)


def execute_create_rework_ticket(annotator_id: str, reason: str, deadline: str) -> str:
    """Thực thi tạo phiếu yêu cầu Rework cho Annotator"""
    clean_id = annotator_id.strip().upper()
    ticket_id = f"RW-2026-{clean_id[-4:] if len(clean_id) >= 4 else '0000'}"
    return json.dumps({
        "status": "SUCCESS",
        "ticket_id": ticket_id,
        "annotator_id": clean_id,
        "reason": reason,
        "deadline": deadline,
        "message": f"Đã tạo thành công phiếu Rework {ticket_id} cho Annotator {clean_id} với lý do '{reason}', hạn chót: {deadline}."
    }, ensure_ascii=False)


# Router gọi tool thực tế
TOOL_ROUTER = {
    "query_qc_error": execute_query_qc_error,
    "create_rework_ticket": execute_create_rework_ticket
}

def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)