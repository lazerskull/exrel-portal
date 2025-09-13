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
        # Handle JSON submission
        data = request.get_json(force=True)

        # Parse rawRequest if it exists
        raw_request = data.get("rawRequest") or data.get("request", {}).get("rawRequest")
        if raw_request:
            form_data = json.loads(raw_request)
        else:
            form_data = data

        # Log for debugging
        print("=== PARSED JOTFORM DATA ===")
        print(json.dumps(form_data, indent=2))
        print("===========================")

        # === Common fields ===
        name = f"{form_data.get('q3_name', {}).get('first','')} {form_data.get('q3_name', {}).get('last','')}"
        id_number = form_data.get("q7_idNumber", "N/A")
        department = form_data.get("q57_department57", "N/A")
        project = form_data.get("q9_project", "N/A")
        telegram_handle = form_data.get("q10_telegramHandle", "N/A")
        service_to_avail = form_data.get("q12_serviceTo", "N/A")

        topic_id = TOPIC_MAP.get(service_to_avail)

        # === Build service-specific message ===
        message = (
            f"📩 *New Request Submission*\n\n"
            f"👤 Name: {name}\n"
            f"🆔 ID Number: {id_number}\n"
            f"🏢 Department: {department}\n"
            f"📂 Project: {project}\n"
            f"💬 Telegram Handle: {telegram_handle}\n"
            f"🛠 Service: {service_to_avail}"
        )

        # Service-specific additions
        if service_to_avail == "Alumni Relations":
            message += "\nKindly state below your alumni relations request or concerns & how you want it to be delivered:\n"
            message += form_data.get("q19_kindlyState", "")
        elif service_to_avail == "Document Checking":
            # File uploads in JotForm come as URLs in the submission
            file_url = form_data.get("document upload", "")
            message += f"\nDocument Upload: {file_url}"
            message += "\n(Optional) Please input specific instructions or concerns regarding the checking of the uploaded document/s:\n"
            message += form_data.get("q24_optionalPlease", "")
        elif service_to_avail == "Partnerships IC":
            message += f"\nw2m link: {form_data.get('q56_w2mLink', '')}"
            # Multiple-choice field for IC participants
            selected_ic = form_data.get("pleaseSelect", "")
            message += f"\nPlease select who you would like to set an IC with: {selected_ic}"
            message += f"\nPlease briefly indicate your reason for requesting an IC: {form_data.get('q62_pleaseBriefly', '')}"
        elif service_to_avail == "Partnerships Request":
            message += f"\nType of Partnerships Service: {form_data.get('q59_typeOf59', '')}"
            message += f"\nPartnership Details: {form_data.get('q30_partnershipDetails', '')}"

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
    port = int(os.getenv("PORT", 5000))  # Render assigns PORT
    app.run(host="0.0.0.0", port=port)
