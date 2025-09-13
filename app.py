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

# === Helper function to safely get values ===
def safe_get(d, key, default="N/A"):
    return d.get(key, default) or default

# === POST route for Jotform submissions ===
@app.route("/jotform", methods=["POST"])
def jotform_webhook():
    try:
        # Handle JSON or form-encoded submissions
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        # Log raw payload
        print("=== RAW JOTFORM PAYLOAD ===")
        print(json.dumps(data, indent=2))
        print("===========================")

        # Some JotForm payloads use rawRequest
        form_data = {}
        if "request" in data and "rawRequest" in data["request"]:
            form_data = json.loads(data["request"]["rawRequest"])
        else:
            form_data = data  # fallback

        # === Extract common fields ===
        name = f"{safe_get(form_data.get('q3_name', {}), 'first')} {safe_get(form_data.get('q3_name', {}), 'last')}"
        id_number = safe_get(form_data, "q7_idNumber")
        department = safe_get(form_data, "q57_department57")
        project = safe_get(form_data, "q9_project")
        telegram_handle = safe_get(form_data, "q10_telegramHandle")
        service_to_avail = safe_get(form_data, "q12_serviceTo")

        # Pick topic ID
        topic_id = TOPIC_MAP.get(service_to_avail)

        # === Format base message ===
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
            message += f"\nKindly state below your alumni relations request or concerns & how you want it to be delivered:\n{safe_get(form_data, 'q19_kindlyState')}"
        elif service_to_avail == "Document Checking":
            uploaded_files = form_data.get("documentUpload", [])
            files_text = "\n".join(uploaded_files) if uploaded_files else "No file uploaded"
            message += f"\nDocument Upload: {files_text}"
            message += f"\n(Optional) Specific instructions or concerns regarding the checking: {safe_get(form_data, 'q24_optionalPlease')}"
        elif service_to_avail == "Partnerships IC":
            message += f"\nw2m link: {safe_get(form_data, 'q56_w2mLink')}"
            # Collect multiple selected IC recipients
            selected_ic = form_data.get("q64_pleaseSelect", [])
            if isinstance(selected_ic, list):
                ic_text = ", ".join(selected_ic)
            else:
                ic_text = str(selected_ic)
            message += f"\nPlease select who you would like to set an IC with: {ic_text}"
            message += f"\nPlease briefly indicate your reason for requesting an IC: {safe_get(form_data, 'q62_pleaseBriefly')}"
        elif service_to_avail == "Partnerships Request":
            message += f"\nType of Partnerships Service: {safe_get(form_data, 'q59_typeOf59')}"
            message += f"\nPartnership Details: {safe_get(form_data, 'q30_partnershipDetails')}"

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
    port = int(os.getenv("PORT", 5000))  # Use Render's assigned port
    app.run(host="0.0.0.0", port=port)
