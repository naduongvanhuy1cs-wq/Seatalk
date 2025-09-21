from flask import Flask, request, jsonify
import requests
import gspread
import re
from datetime import datetime

# ================== CONFIG GOOGLE SHEET ==================
SHEET_ID = "1kcZ-Z0PbE7Wcjr8H0KjXimuZ-JALup9jS54xyDzc-ik"
SHEET_NAME = "Issue"

# ================== CONFIG SEATALK ==================
APP_ID = "MDk0NDMyMjU5MjM3"
APP_SECRET = "MgFYYHHzbT8ZDPu-1ACFtust4fKtGgql"

# ================== FLASK APP ==================
app = Flask(__name__)

# ================== GOOGLE SHEET AUTH ==================
import os
import json
from google.oauth2.service_account import Credentials
import gspread

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Đọc credentials từ biến môi trường
creds_json = json.loads(os.environ["GOOGLE_CREDENTIALS"])

# Tạo credentials từ service account JSON
creds = Credentials.from_service_account_info(creds_json, scopes=scope)

# Khởi tạo client gspread
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# ================== SEATALK AUTH ==================
def get_access_token():
    url = "https://openapi.seatalk.io/auth/app_access_token"
    payload = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }
    resp = requests.post(url, json=payload)
    data = resp.json()
    token = data.get("app_access_token")
    expire = data.get("expire_in")
    print(f"✅ Lấy Access Token thành công: {token[:10]}... (hết hạn sau {expire}s)")
    return token

# ================== GỬI TIN NHẮN VÀO SEATALK GROUP/THREAD ==================
def send_message_to_seatalk(group_id: str, text: str, thread_id: str = None, quoted_message_id: str = None):
    """
    Gửi message vào group; nếu thread_id có thì trả lời trong thread,
    nếu không có thread_id nhưng có message_id thì set thread_id = message_id để mở thread mới.
    """
    token = get_access_token()
    if not token:
        print("❌ Không có access token, không gửi được.")
        return

    url = "https://openapi.seatalk.io/messaging/v2/group_chat/send"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    message_obj = {
        "tag": "text",
        "text": {
            "format": 1,
            "content": text
        }
    }

    if quoted_message_id:
        message_obj["quoted_message_id"] = quoted_message_id

    if thread_id:
        message_obj["thread_id"] = thread_id

    payload = {
        "group_id": group_id,
        "message": message_obj
    }

    resp = requests.post(url, headers=headers, json=payload)
    try:
        print(f"📤 Sent to Seatalk: {resp.status_code} {resp.text}")
    except Exception:
        print("📤 Sent to Seatalk, response unreadable.")
    return resp

# ================== TRA CỨU GOOGLE SHEET ==================
def check_approval(employee_name_keyword: str, issue_keyword: str, date_keyword: str):
    rows = sheet.get_all_values()
    today_date = datetime.now().date()
    found_matches = []

    for row in rows[1:]:
        if len(row) > 14:
            name = row[1].strip()
            issue = row[3].strip()
            date_str = row[7].strip()
            approved = row[14].strip()

            if employee_name_keyword.lower() in name.lower() and \
               issue_keyword.lower() in issue.lower():

                try:
                    sheet_date = datetime.strptime(date_str, "%m/%d/%Y").date()
                except ValueError:
                    continue

                if date_keyword.lower() == "hôm nay":
                    if sheet_date == today_date:
                        found_matches.append(f"{name} - {issue} ngày {date_str} - {approved}")

                elif re.match(r"\d{1,2}/\d{1,2}/\d{4}", date_keyword):
                    try:
                        input_date = datetime.strptime(date_keyword, "%m/%d/%Y").date()
                        if sheet_date == input_date:
                            found_matches.append(f"{name} - {issue} ngày {date_str} - {approved}")
                    except ValueError:
                        continue
                else:
                    found_matches.append(f"{name} - {issue} ngày {date_str} - {approved}")
    
    if len(found_matches) == 1:
        return found_matches[0]
    elif len(found_matches) > 1:
        return "Tìm thấy nhiều kết quả:\n" + "\n".join(found_matches) + "\nVui lòng cung cấp thêm thông tin."
    else:
        return "Xin lỗi, không tìm thấy thông tin phù hợp."

# ================== FLASK ROUTES ==================
@app.route("/callback", methods=["POST","GET"])
def bot_callback_handler():
    body = request.json
    print("📩 Nhận webhook:", body)

    event_type = body.get("event_type")

    if event_type == "event_verification":
        challenge = body.get("event", {}).get("seatalk_challenge")
        print("✅ Xác minh webhook thành công.")
        return jsonify({"seatalk_challenge": challenge})

    if event_type == "new_mentioned_message_received_from_group_chat":
        event = body.get("event", {})
        group_id = event.get("group_id")
        msg = event.get("message", {}) or {}

        message_id = msg.get("message_id")
        event_thread_id = msg.get("thread_id") or ""
        text = msg.get("text", {}).get("plain_text", "")

        response_text = "Xin lỗi, mình không hiểu câu hỏi.\nVui lòng hỏi dạng: @bot [Tên] [từ khóa] [hôm nay] có được duyệt không?"

        match = re.search(
            r"(?:@\S+\s+)?(?:bot\s+)?(.+?)\s+(WFH|Làm thêm)\s+(hôm nay|\d{1,2}/\d{1,2}/\d{4})?\s*có được duyệt không",
            text,
            re.IGNORECASE
        )
        
        if match:
            employee_name_keyword = match.group(1).strip()
            issue_keyword = match.group(2).strip()
            date_keyword = match.group(3) if match.group(3) else ""

            employee_name_keyword = re.sub(r"@\S+", "", employee_name_keyword).strip()
            response_text = check_approval(employee_name_keyword, issue_keyword, date_keyword)
        
        print("✅ Bot trả lời:", response_text)

        if group_id:
            use_thread_id = event_thread_id if event_thread_id else (message_id if message_id else None)
            send_message_to_seatalk(
                group_id=group_id,
                text=response_text,
                thread_id=use_thread_id,
                quoted_message_id=message_id
            )

    return jsonify({"status": "ok"})

# ================== MAIN ==================
if __name__ == "__main__":
    print("🚀 Flask server starting...")
    app.run(host="0.0.0.0", port=5000, debug=True)
