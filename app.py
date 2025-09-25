from flask import Flask, request, jsonify
import requests
import os
import json

app = Flask(__name__)

# === Bot details from environment variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === Topic map (Service → Telegram topic ID) ===
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
        # Step 1: get JSON or form data
        if request.is_json:
            data = request.get_json(force=True)
        else:
            data = request.form.to_dict()

        # Step 2: try to parse rawRequest if present
        form_data = data
        raw_request_str = None
        if "request" in data and "rawRequest" in data["request"]:
            raw_request_str = data["request"]["rawRequest"]
        elif "rawRequest" in data:
            raw_request_str = data["rawRequest"]

        if raw_request_str:
            try:
                form_data = json.loads(raw_request_str)
            except Exception as e:
                print("Warning: failed to parse rawRequest, using top-level data. Error:", e)

        # Step 3: log everything for debugging
        print("=== PARSED FORM DATA ===")
        print(json.dumps(form_data, indent=2))
        print("=======================")

        # Step 4: safe extraction helper
        def safe_get(d, key):
            val = d.get(key, "")
            return val if val is not None else ""

        # Step 5: extract common fields
        name = f"{safe_get(form_data.get('q3_name', {}), 'first')} {safe_get(form_data.get('q3_name', {}), 'last')}".strip()
        id_number = safe_get(form_data, "q7_idNumber")
        department = safe_get(form_data, "q57_department57")
        project = safe_get(form_data, "q9_project")
        telegram_handle = safe_get(form_data, "q10_telegramHandle")
        service_to_avail = safe_get(form_data, "q12_serviceTo")

        topic_id = TOPIC_MAP.get(service_to_avail)

        # Step 6: build Telegram message
        message = f"📩 *New Request Submission*\n\n" \
                  f"👤 Name: {name}\n" \
                  f"🆔 ID Number: {id_number}\n" \
                  f"🏢 Department: {department}\n" \
                  f"📂 Project: {project}\n" \
                  f"💬 Telegram Handle: {telegram_handle}\n" \
                  f"🛠 Service: {service_to_avail}"

        # Add service-specific fields
        if service_to_avail == "Alumni Relations":
            message += f"\nKindly state below your alumni relations request or concerns & how you want it to be delivered:\n{safe_get(form_data, 'q19_kindlyState')}"
        elif service_to_avail == "Document Checking":
            message += f"\nDocument Upload: https://www.jotform.com/tables/252532984107055"
            message += f"\n(Optional) Specific instructions or concerns regarding the checking: {safe_get(form_data, 'q24_optionalPlease')}"
        elif service_to_avail == "Partnerships IC":
            message += f"\nw2m link: {safe_get(form_data, 'q56_w2mLink')}"
            ic_selected = form_data.get('q64_pleaseSelect', [])
            if isinstance(ic_selected, list):
                ic_selected = ', '.join(ic_selected)
            message += f"\nPlease select IC with: {ic_selected}"
            message += f"\nReason: {safe_get(form_data, 'q62_pleaseBriefly')}"
        elif service_to_avail == "Partnerships Request":
            message += f"\nType of Partnerships Service: {safe_get(form_data, 'q59_typeOf59')}"
            message += f"\nPartnership Details: {safe_get(form_data, 'q30_partnershipDetails')}"

        # Step 7: send to Telegram
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        if topic_id:
            payload["message_thread_id"] = topic_id

        resp = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload)
        print("Telegram response:", resp.json())

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("Webhook Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Render assigned port
    app.run(host="0.0.0.0", port=port)
