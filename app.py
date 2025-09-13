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
        # Handle JSON or form-encoded submissions
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        # Log the raw payload for debugging
        print("=== RAW JOTFORM PAYLOAD ===")
        print(json.dumps(data, indent=2))
        print("===========================")

        # Extract form data
        form_data = {}
        if "request" in data and "rawRequest" in data["request"]:
            form_data = json.loads(data["request"]["rawRequest"])
        else:
            form_data = data

        # Common fields
        name = f"{form_data.get('q3_name', {}).get('first','')} {form_data.get('q3_name', {}).get('last','')}"
        id_number = form_data.get("q7_idNumber", "N/A")
        department = form_data.get("q57_department57", "N/A")
        project = form_data.get("q9_project", "N/A")
        telegram_handle = form_data.get("q10_telegramHandle", "N/A")
        service_to_avail = form_data.get("q12_serviceTo", "N/A")

        topic_id = TOPIC_MAP.get(service_to_avail)

        # Start message
        message = (
            f"📩 *New Request Submission*\n\n"
            f"👤 Name: {name}\n"
            f"🆔 ID Number: {id_number}\n"
            f"🏢 Department: {department}\n"
            f"📂 Project: {project}\n"
            f"💬 Telegram Handle: {telegram_handle}\n"
            f"🛠 Service: {service_to_avail}"
        )

        # === Service-specific fields ===
        if service_to_avail == "Alumni Relations":
            kindly_state = form_data.get("q19_kindlyState", "")
            if kindly_state:
                message += f"\n\nKindly state below your alumni relations request or concerns & how you want it to be delivered:\n{kindly_state}"

        elif service_to_avail == "Document Checking":
            doc_file = form_data.get("document upload", "No file provided")
            optional_instructions = form_data.get("q24_optionalPlease", "")
            
            # If doc_file looks like a URL, format as clickable link in Telegram
            if doc_file.startswith("http://") or doc_file.startswith("https://"):
                doc_display = f"[Download File]({doc_file})"
            else:
                doc_display = doc_file
            
            message += f"\n\nDocument Upload: {doc_display}"
            if optional_instructions:
                message += f"\n(Optional) Instructions/Concerns:\n{optional_instructions}"

        elif service_to_avail == "Partnerships IC":
            w2m_link = form_data.get("q56_w2mLink", "")
            ic_with = form_data.get("pleaseSelect", "")  # could be list if multiple
            reason = form_data.get("q62_pleaseBriefly", "")
            if isinstance(ic_with, list):
                ic_with = ", ".join(ic_with)
            message += f"\n\nw2m link: {w2m_link}"
            message += f"\nPlease select who you would like to set an IC with: {ic_with}"
            message += f"\nPlease briefly indicate your reason for requesting an IC:\n{reason}"

        elif service_to_avail == "Partnerships Request":
            service_type = form_data.get("q59_typeOf59", "")
            details = form_data.get("q30_partnershipDetails", "")
            message += f"\n\nType of Partnerships Service: {service_type}"
            message += f"\nPartnership Details: {details}"

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
    port = int(os.getenv("PORT", 5000))  # Use Render's assigned port
    app.run(host="0.0.0.0", port=port)
