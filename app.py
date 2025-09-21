from flask import Flask, request, jsonify
import os
import json
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# ================== Google Sheet Config ==================
# Lấy credentials từ biến môi trường GOOGLE_CREDENTIALS
creds_json = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(
    creds_json,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
client = gspread.authorize(creds)

# Lấy thông tin Google Sheet
SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME")
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)


# ================== SeaTalk Webhook ==================
@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.json
    print("📩 Nhận webhook:", body)

    event_type = body.get("event_type")

    # --- Xử lý xác minh webhook ---
    if event_type == "event_verification":
        challenge = body.get("seatalk_challenge")
        print(f"✅ Xác minh webhook thành công. Challenge={challenge}")
        return jsonify({"seatalk_challenge": challenge}), 200

    # --- Xử lý sự kiện thực tế ---
    if event_type == "event_callback":
        event_data = body.get("event", {})
        event_name = event_data.get("event_name", "unknown")

        # Lưu vào Google Sheet
        sheet.append_row([event_name, json.dumps(event_data)])
        print("📝 Đã lưu sự kiện vào Google Sheet.")

        return jsonify({"status": "success"}), 200

    return jsonify({"status": "ignored"}), 200


# ================== Test route ==================
@app.route("/", methods=["GET"])
def home():
    return "✅ Seatalk bot is running!", 200


# ================== Main ==================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
