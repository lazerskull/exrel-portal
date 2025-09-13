from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# === Bot details ===
BOT_TOKEN = "8291138183:AAHYP8lrZebflWdldBeHUNr9jdmnsK8Vm9o"
CHAT_ID = "-1003030283356"

TOPIC_MAP = {
    "Academic Relations": 4,
    "Alumni Relations": 8,
    "Document Checking": 6,
    "Partnerships Request": 10,
    "Partnerships IC": 2
}

@app.route("/jotform", methods=["POST"])
def jotform_webhook():
    try:
        # Get Jotform payload
        data = request.get_json(force=True)

        form_data = {}
        if "rawRequest" in data.get("request", {}):
            form_data = json.loads(data["request"]["rawRequest"])

        # Extract fields
        secret = form_data.get("q65_secret", "N/A")
        name = f"{form_data.get('q3_name', {}).get('first','')} {form_data.get('q3_name', {}).get('last','')}"
        id_number = form_data.get("q7_idNumber", "N/A")
        department = form_data.get("q57_department57", "N/A")
        project = form_data.get("q9_project", "N/A")
        telegram_handle = form_data.get("q10_telegramHandle", "N/A")
        service_to_avail = form_data.get("q12_serviceTo", "N/A")

        topic_id = TOPIC_MAP.get(service_to_avail)

        # Format message
        message = (
            f"📩 *New Request Submission*\n\n"
            f"🔑 Secret: `{secret}`\n"
            f"👤 Name: {name}\n"
            f"🆔 ID Number: {id_number}\n"
            f"🏢 Department: {department}\n"
            f"📂 Project: {project}\n"
            f"💬 Telegram Handle: {telegram_handle}\n"
            f"🛠 Service: {service_to_avail}"
        )

        # Send to Telegram
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
    app.run(host="0.0.0.0", port=5000)
