from flask import Flask, request, jsonify
import requests
import os
import json

app = Flask(__name__)

# === Bot details from environment variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === Topic map (Service to Avail → Telegram topic ID) ===
TOPIC_MAP = {
    "Academic Relations": int(os.getenv("TOPIC_ID_ACAD", 0)),
    "Alumni Relations": int(os.getenv("TOPIC_ID_ALUMNI", 0)),
    "Document Checking": int(os.getenv("TOPIC_ID_DOCS", 0)),
    "Partnerships IC": int(os.getenv("TOPIC_ID_IC", 0)),
    "Partnerships Request": int(os.getenv("TOPIC_ID_REQUEST", 0))
}

# === Root route for health check ===
@app.route("/")
def home():
    return "🚀 Jotform → Telegram bot is running!", 200

# === GET route for /jotform to test in browser ===
@app.route("/jotform", methods=["GET"])
def jotform_get():
    return "🚀 Jotform webhook endpoint. Use POST to submit data.", 200

# === POST route for Jotform submissions ===
@app.route("/jotform", methods=["POST"])
def jotform_webhook():
    try:
        # Log the raw payload
        print("=== Raw POST payload ===")
        print("request.data:", request.data)
        print("request.form:", request.form)
        print("request.json:", request.get_json(silent=True))

        # Try JSON first, fallback to form data
        data = request.get_json(silent=True)
        if data:
            # Handle JSON payload
            form_data = data.get("request", {}).get("rawRequest")
            if form_data:
                form_data = json.loads(form_data)
            else:
                form_data = data
        else:
            # Handle form-encoded submission
            form_data = request.form.to_dict()

        # === Extract fields ===
        name = f"{form_data.get('q3_name', {}).get('first','')} {form_data.get('q3_name', {}).get('last','')}" if isinstance(form_data.get('q3_name'), dict) else form_data.get('q3_name', 'N/A')
        id_number = form_data.get("q7_idNumber", "N/A")
        department = form_data.get("q57_department57", "N/A")
        project = form_data.get("q9_project", "N/A")
        telegram_handle = form_data.get("q10_telegramHandle", "N/A")
        service_to_avail = form_data.get("q12_serviceTo", "N/A")

        # Pick topic ID based on service
        topic_id = TOPIC_MAP.get(service_to_avail)

        # === Format message ===
        message = (
            f"📩 *New Request Submission*\n\n"
            f"👤 Name: {name}\n"
            f"🆔 ID Number: {id_number}\n"
            f"🏢 Department: {department}\n"
            f"📂 Project: {project}\n"
            f"💬 Telegram Handle: {telegram_handle}\n"
            f"🛠 Service: {service_to_avail}"
        )

        # === Send to Telegram ===
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        if topic_id:
            payload["message_thread_id"] = topic_id

        response = requests.post(url, json=payload)
        print("Telegram response:", response.json())

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    # Render sets the PORT environment variable automatically
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
