from flask import Flask, request, jsonify
from fuzzywuzzy import process
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

app = Flask(__name__)

user_details = {}

# Google Sheets Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds_raw = os.environ.get("GOOGLE_CREDENTIALS_JSON")

if not google_creds_raw:
    raise Exception("Google Credentials not found in environment variables.")

google_creds_dict = json.loads(google_creds_raw)
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("chatbot_userdata").sheet1

# FAQ database
faq = {
    "can i upgrade or downgrade my plan": "Yes, our flexible plans allow easy upgrades.",
    "what is cloud hosting": "Cloud hosting uses virtual servers on the internet, offering scalability.",
    "do you offer technical support": "Yes, 24/7 technical support is available.",
    "what are your service hours": "We are available 24/7, including holidays.",
    "how can i cancel my subscription": "Cancel anytime via your dashboard or by contacting support.",
    "do you offer custom plans": "Yes, customized plans are available. Contact sales for details."
}

@app.route('/')
def index():
    return 'Webhook server is running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json()
    intent = req.get('queryResult', {}).get('intent', {}).get('displayName', "")
    user_query = req.get('queryResult', {}).get('queryText', "").lower()
    session = req.get('session', "")

    if session not in user_details:
        user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "row_number": None}

    step = user_details[session]["step"]

    # Handle greeting on Welcome Intent
    if intent == "Default Welcome Intent":
        user_details[session] = {"step": "ask_name", "name": "", "contact": "", "email": "", "row_number": None}
        return jsonify({"fulfillmentText": "Hi! Welcome to our services. May I know your Name?"})

    # Step 1: Ask Name
    if step == "ask_name":
        user_details[session]["name"] = user_query.title()
        user_details[session]["step"] = "ask_contact"
        return jsonify({"fulfillmentText": "Thank you! Please enter your 10-digit Contact Number."})

    # Step 2: Ask Contact
    if step == "ask_contact":
        if not user_query.isdigit() or len(user_query) != 10:
            return jsonify({"fulfillmentText": "❗ Please enter a valid 10-digit Contact Number."})
        user_details[session]["contact"] = user_query
        user_details[session]["step"] = "ask_email"
        return jsonify({"fulfillmentText": "Almost done! Please enter your Email address."})

    # Step 3: Ask Email
    if step == "ask_email":
        user_details[session]["email"] = user_query
        try:
            row_data = [user_details[session]["name"], user_details[session]["contact"], user_details[session]["email"], "", ""]
            sheet.append_row(row_data)
            user_details[session]["row_number"] = sheet.row_count
        except Exception as e:
            print(f"Error storing to sheet: {e}")

        user_details[session]["step"] = "main_menu"
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Thank you! What would you like to ask about?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [{"text": "Basic FAQ"}, {"text": "Service Available"}]}
                ]]}}
            ]
        })

    # Main Menu
    if step == "main_menu":
        if user_query == "basic faq":
            return jsonify({"fulfillmentText": "Sure! You can ask general questions like 'What is cloud hosting'."})
        
        if user_query == "service available":
            user_details[session]["step"] = "service_options"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["We provide these services:"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [
                            {"text": "Data Centre"},
                            {"text": "Cloud Services"},
                            {"text": "Dedicated Server"},
                            {"text": "Co-location"}
                        ]}
                    ]]}}
                ]
            })

    # Service Options
    if step == "service_options":
        if user_query == "data centre":
            return jsonify({"fulfillmentText": "A Data Centre centralizes IT operations for managing your data."})

        if user_query == "cloud services":
            user_details[session]["step"] = "cloud_options"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Please choose Cloud Service:"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [{"text": "DC"}, {"text": "DR"}, {"text": "Both"}]}
                    ]]}}
                ]
            })

        if user_query == "dedicated server":
            return jsonify({"fulfillmentText": "Dedicated Servers provide high-performance hosting for your applications."})

        if user_query == "co-location":
            return jsonify({"fulfillmentText": "Co-location allows you to house your equipment in our secure data centres."})

    # Cloud Options
    if step == "cloud_options":
        if user_query in ["dc", "dr", "both"]:
            user_details[session]["step"] = "cloud_service_type"
            user_details[session]["cloud_selection"] = user_query.upper()
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Choose service type:"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [{"text": "Hyperscaler"}, {"text": "Traditional IaaS"}]}
                    ]]}}
                ]
            })

    # Cloud Service Type
    if step == "cloud_service_type":
        if user_query == "hyperscaler":
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Select Cloud Provider:"]}},
                    {"payload": {"richContent": [[
                        {"type": "button", "icon": {"type": "cloud"}, "text": "AWS", "link": "https://example.com/aws"},
                        {"type": "button", "icon": {"type": "cloud"}, "text": "Azure", "link": "https://example.com/azure"},
                        {"type": "button", "icon": {"type": "cloud"}, "text": "Google Cloud", "link": "https://example.com/googlecloud"},
                        {"type": "button", "icon": {"type": "cloud"}, "text": "Oracle", "link": "https://example.com/oracle"}
                    ]]}}
                ]
            })

        if user_query == "traditional iaas":
            user_details[session]["step"] = "ask_traditional_req"
            return jsonify({"fulfillmentText": "Kindly provide your requirement for Traditional IaaS."})

    # Requirement for Traditional IaaS
    if step == "ask_traditional_req":
        try:
            row_number = user_details[session].get("row_number")
            if row_number:
                sheet.update_cell(row_number, 4, user_query)
        except Exception as e:
            print(f"Error storing Traditional IAAS requirement: {e}")

        user_details[session]["step"] = "main_menu"
        return jsonify({"fulfillmentText": "Thank you! Our team will contact you shortly."})

    # Fuzzy FAQ fallback
    if faq:
        best_match, score = process.extractOne(user_query, faq.keys())
        if score >= 70:
            return jsonify({"fulfillmentText": faq[best_match]})
        else:
            return jsonify({"fulfillmentText": "Sorry, I didn't quite catch that. Could you please rephrase?"})

    return jsonify({"fulfillmentText": "I'm not sure how to help with that. Please try again."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
