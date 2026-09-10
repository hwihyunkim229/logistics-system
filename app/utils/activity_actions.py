"""Canonical activity labels shared by the table, filters and Excel export.

Stored action codes remain unchanged for audit and filtering.
"""
import re

ACTION_LABELS = {
    "LOGIN": "로그인",
    "LOGOUT": "로그아웃",
    "CREATE_USER": "계정 생성",
    "RESET_PASSWORD": "비밀번호 초기화",
    "CHANGE_PASSWORD": "비밀번호 변경",
    "DELETE_USER": "계정 삭제",
    "UPDATE_USER_PERMISSIONS": "계정 권한 수정",
    "UPLOAD_EXCEL": "엑셀 업로드",
    "DOWNLOAD_EXCEL": "엑셀 다운로드",
    "OUTBOUND": "출고",
    "INBOUND": "입고",
    "MOVE_IN": "입고 이동",
    "MOVE_OUT": "출고 이동",
    "DELETE_SELECTED": "선택 삭제",
    "DELETE_ALL": "전체 삭제",
    "BULK_UPDATE": "일괄 수정",
    "UPDATE_FIELD": "항목 수정",
    "UPDATE_SIZE": "사이즈 수정",
    "STOCK_MOVE_IN": "가계상 재고 · 입고",
    "STOCK_MOVE_OUT": "가계상 재고 · 출고",
    "STOCK_DELETE_SELECTED": "가계상 재고 · 선택 삭제",
    "STOCK_DOWNLOAD_EXCEL": "가계상 재고 · 엑셀 다운로드",
    "STOCK_INIT_EXCEL": "가계상 재고 · 엑셀 초기 등록",
    "STOCK_UPLOAD_EXCEL": "가계상 재고 · 엑셀 업로드",
    "STOCK_UPDATE_QTY": "가계상 재고 · 수량 수정",
    "STOCK_UPDATE_GRADE": "가계상 재고 · 등급 수정",
    "STOCK_BULK_UPDATE_GRADE": "가계상 재고 · 등급 일괄 수정",
    "STOCK_BULK_UPDATE_QTY": "가계상 재고 · 수량 일괄 수정",
    "STOCK_HISTORY_DOWNLOAD_EXCEL": "가계상 재고 · 이력 엑셀 다운로드",
    "STOCK_ITEM_MASTER_UPDATE": "가계상 재고 · 품목 기준정보 수정",
    "STOCK_ITEM_MASTER_UPLOAD": "가계상 재고 · 품목 기준정보 엑셀 업로드",
    "INVENTORY_ADD": "수불 재고 · 등록",
    "INVENTORY_MOVE_IN": "수불 재고 · 입고",
    "INVENTORY_MOVE_OUT": "수불 재고 · 출고",
    "INVENTORY_DELETE_SELECTED": "수불 재고 · 선택 삭제",
    "INVENTORY_UPDATE_FIELD": "수불 재고 · 항목 수정",
    "INVENTORY_BULK_UPDATE_QTY": "수불 재고 · 수량 일괄 수정",
    "INVENTORY_BULK_UPDATE_NOTE": "수불 재고 · 비고 일괄 수정",
    "INVENTORY_BULK_UPDATE_LOT": "수불 재고 · LOT 일괄 수정",
    "INVENTORY_HISTORY_DOWNLOAD_EXCEL": "수불 재고 · 이력 엑셀 다운로드",
    "INVENTORY_DOWNLOAD_EXCEL": "수불 재고 · 엑셀 다운로드",
    "INVENTORY_INIT_EXCEL": "수불 재고 · 엑셀 초기 등록",
    "INVENTORY_UPLOAD_EXCEL": "수불 재고 · 엑셀 업로드",
    "MRP_BOM_UPLOAD": "MRP · BOM 엑셀 업로드",
    "MRP_BOM_DOWNLOAD": "MRP · BOM 엑셀 다운로드",
    "MRP_PRODUCTION_PLAN_UPLOAD": "MRP · 생산계획 엑셀 업로드",
    "MRP_PRODUCTION_PLAN_DOWNLOAD": "MRP · 생산계획 엑셀 다운로드",
    "MRP_RESULT_DOWNLOAD": "MRP · 소요량 결과 엑셀 다운로드",
    "MRP_MONTHLY_RESULT_DOWNLOAD": "MRP · 월별 예상재고 엑셀 다운로드",
    "MRP_MATERIAL_MASTER_ADD": "MRP · 자재 기준정보 등록",
    "MRP_MATERIAL_MASTER_UPDATE": "MRP · 자재 기준정보 수정",
    "MRP_MATERIAL_MASTER_UPLOAD": "MRP · 자재 기준정보 엑셀 업로드",
    "MRP_MATERIAL_MASTER_DOWNLOAD": "MRP · 자재 기준정보 엑셀 다운로드",
    "MRP_MATERIAL_NOTE_SAVE": "MRP · 자재 비고 저장",
    "RENTAL_ITEM_CREATE": "대여 재고 · 품목 등록",
    "RENTAL_QTY_UPDATE": "대여 재고 · 수량 수정",
    "RENTAL_UPLOAD_EXCEL": "대여 재고 · 엑셀 업로드",
    "RENTAL_DOWNLOAD_EXCEL": "대여 재고 · 엑셀 다운로드",
    "RENTAL_MOVE_OUT": "대여 재고 · 출고",
    "RENTAL_HISTORY_UPLOAD_EXCEL": "대여 재고 · 이력 엑셀 업로드",
    "RENTAL_HISTORY_DOWNLOAD_EXCEL": "대여 재고 · 이력 엑셀 다운로드",
}


def action_label(code):
    code = str(code or "").strip()
    if code in ACTION_LABELS:
        return ACTION_LABELS[code]
    # Preserve historical Korean descriptions; expose unknown codes only as metadata.
    return code if re.search(r"[가-힣]", code) else "기타 작업"


def action_style(code):
    code = str(code or "")
    if code in {"LOGIN", "LOGOUT"}:
        return code.lower()
    for token, style in [("DELETE", "delete"), ("PASSWORD", "reset"),
                         ("DOWNLOAD", "download"), ("UPLOAD", "upload"),
                         ("INIT_EXCEL", "upload"), ("MOVE", "move"),
                         ("CREATE", "create"), ("ADD", "create")]:
        if token in code:
            return style
    return {"INBOUND": "in", "OUTBOUND": "out"}.get(code, "update")
