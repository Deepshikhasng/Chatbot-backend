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

faq = {
    "can i upgrade or downgrade my plan": "Yes, easy upgrades are available.",
    "what is cloud hosting": "Cloud hosting uses virtual servers with scalability.",
    "do you offer technical support": "Yes, 24/7 technical support is available.",
    "what are your service hours": "We are available 24/7, including holidays.",
    "how can i cancel my subscription": "Cancel via dashboard or support.",
    "do you offer custom plans": "Yes, contact sales for customized plans."
}

@app.route('/')
def index():
    return 'Webhook is running'

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json()
    intent = req.get('queryResult', {}).get('intent', {}).get('displayName', "")
    user_query = req.get('queryResult', {}).get('queryText', "").lower()
    session = req.get('session', "")

    if session not in user_details:
        user_details[session] = {"step": "main_menu", "name": "", "contact": "", "email": "", "row_number": None}

    step = user_details[session]["step"]

    if intent == "Default Welcome Intent":
        user_details[session]["step"] = "main_menu"
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Hi! I am here to assist you. What would you like to ask about?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [
                        {"text": "Basic FAQ"},
                        {"text": "Service Available"}
                    ]}
                ]]}}
            ]
        })

    if step == "main_menu":
        if user_query == "basic faq":
            return jsonify({"fulfillmentText": "Sure! What would you like to ask about our services?"})

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

    if step == "service_options":
        if user_query == "data centre":
            user_details[session]["step"] = "ask_name_dc"
            return jsonify({"fulfillmentText": "Please enter your Name."})

        if user_query == "cloud services":
            user_details[session]["step"] = "ask_name_cloud"
            return jsonify({"fulfillmentText": "Please enter your Name."})

        if user_query == "dedicated server":
            return jsonify({
                "fulfillmentMessages": [
                    {"payload": {"richContent": [[
                        {"type": "button", "icon": {"type": "link"}, "text": "Dedicated Server", "link": "https://www.vensyscotechnologies.com/cloudservices/cloud-services.html"}
                    ]]}}
                ]
            })

        if user_query == "co-location":
            return jsonify({
                "fulfillmentMessages": [
                    {"payload": {"richContent": [[
                        {"type": "button", "icon": {"type": "link"}, "text": "New", "link": "https://www.vensyscotechnologies.com/cloudservices/colocation.html"},
                        {"type": "button", "icon": {"type": "link"}, "text": "Existing", "link": "https://www.vensyscotechnologies.com/cloudservices/colocation.html"}
                    ]]}}
                ]
            })

    # Collect User Details After Data Centre
    if step == "ask_name_dc":
        user_details[session]["name"] = user_query.title()
        user_details[session]["step"] = "ask_contact_dc"
        return jsonify({"fulfillmentText": "Please enter your 10-digit Contact Number."})

    if step == "ask_contact_dc":
        if not user_query.isdigit() or len(user_query) != 10:
            return jsonify({"fulfillmentText": "❗ Enter a valid 10-digit Contact Number."})
        user_details[session]["contact"] = user_query
        user_details[session]["step"] = "ask_email_dc"
        return jsonify({"fulfillmentText": "Please enter your Email address."})

    if step == "ask_email_dc":
        user_details[session]["email"] = user_query
        try:
            sheet.append_row([user_details[session]["name"], user_details[session]["contact"], user_details[session]["email"], "", ""])
            user_details[session]["row_number"] = sheet.row_count
        except Exception as e:
            print(f"Error storing details: {e}")
        user_details[session]["step"] = "datacentre_details"
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Would you like On-Premises or Cloud?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [
                        {"text": "On-Premises"},
                        {"text": "Cloud"}
                    ]}
                ]]}}
            ]
        })

    # Cloud User Info Collection
    if step == "ask_name_cloud":
        user_details[session]["name"] = user_query.title()
        user_details[session]["step"] = "ask_contact_cloud"
        return jsonify({"fulfillmentText": "Please enter your 10-digit Contact Number."})

    if step == "ask_contact_cloud":
        if not user_query.isdigit() or len(user_query) != 10:
            return jsonify({"fulfillmentText": "❗ Enter a valid 10-digit Contact Number."})
        user_details[session]["contact"] = user_query
        user_details[session]["step"] = "ask_email_cloud"
        return jsonify({"fulfillmentText": "Please enter your Email address."})

    if step == "ask_email_cloud":
        user_details[session]["email"] = user_query
        try:
            sheet.append_row([user_details[session]["name"], user_details[session]["contact"], user_details[session]["email"], "", ""])
            user_details[session]["row_number"] = sheet.row_count
        except Exception as e:
            print(f"Error storing details: {e}")
        user_details[session]["step"] = "cloud_options"
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Please choose Cloud Service:"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [
                        {"text": "DC"},
                        {"text": "DR"},
                        {"text": "Both"}
                    ]}
                ]]}}
            ]
        })

    if step == "datacentre_details":
        if user_query == "on-premises":
            user_details[session]["step"] = "onprem_options"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Are you a New or Existing customer?"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [
                            {"text": "New"},
                            {"text": "Existing"}
                        ]}
                    ]]}}
                ]
            })

        if user_query == "cloud":
            user_details[session]["step"] = "cloud_options"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Please choose Cloud Service:"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [
                            {"text": "DC"},
                            {"text": "DR"},
                            {"text": "Both"}
                        ]}
                    ]]}}
                ]
            })

    if step == "onprem_options":
        if user_query == "new":
            return jsonify({
                "fulfillmentMessages": [
                    {"payload": {"richContent": [[
                        {"type": "button", "icon": {"type": "link"}, "text": "DC", "link": "https://www.vensyscotechnologies.com/cloudservices/datacenter.html"},
                        {"type": "button", "icon": {"type": "link"}, "text": "DR", "link": "https://www.vensyscotechnologies.com/cloudservices/datacenter.html"},
                        {"type": "button", "icon": {"type": "link"}, "text": "Both", "link": "https://www.vensyscotechnologies.com/cloudservices/datacenter.html"}
                    ]]}}
                ]
            })

        if user_query == "existing":
            user_details[session]["step"] = "existing_req"
            return jsonify({"fulfillmentText": "Please provide your requirement."})

    if step == "existing_req":
        try:
            row = user_details[session].get("row_number")
            if row:
                sheet.update_cell(row, 4, user_query)
        except Exception as e:
            print(f"Error storing requirement: {e}")
        user_details[session]["step"] = "main_menu"
        return jsonify({"fulfillmentText": "Thank you! Our team will contact you."})

    if step == "cloud_options":
        if user_query in ["dc", "dr", "both"]:
            user_details[session]["step"] = "cloud_service_type"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Choose service type:"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [
                            {"text": "Hyperscaler"},
                            {"text": "Traditional IaaS"}
                        ]}
                    ]]}}
                ]
            })

    if step == "cloud_service_type":
        if user_query == "hyperscaler":
            return jsonify({
                "fulfillmentMessages": [
                    {"payload": {"richContent": [[
                        {"type": "button", "icon": {"type": "link"}, "text": "AWS", "link": "https://www.vensyscotechnologies.com/cloudservices/newer_index_testng.html"},
                        {"type": "button", "icon": {"type": "link"}, "text": "Azure", "link": "https://www.vensyscotechnologies.com/cloudservices/newer_index_testng.html"},
                        {"type": "button", "icon": {"type": "link"}, "text": "Google Cloud", "link": "https://www.vensyscotechnologies.com/cloudservices/newer_index_testng.html"},
                        {"type": "button", "icon": {"type": "link"}, "text": "Oracle", "link": "https://www.vensyscotechnologies.com/cloudservices/newer_index_testng.html"}
                    ]]}}
                ]
            })

        if user_query == "traditional iaas":
            user_details[session]["step"] = "ask_traditional_req"
            return jsonify({"fulfillmentText": "Please provide your Traditional IaaS requirement."})

    if step == "ask_traditional_req":
        try:
            row = user_details[session].get("row_number")
            if row:
                sheet.update_cell(row, 5, user_query)
        except Exception as e:
            print(f"Error storing Traditional IaaS requirement: {e}")

        user_details[session]["step"] = "main_menu"
        return jsonify({"fulfillmentText": "Thank you! Our team will contact you shortly."})

    if faq:
        best_match, score = process.extractOne(user_query, faq.keys())
        if score >= 70:
            return jsonify({"fulfillmentText": faq[best_match]})
        else:
            return jsonify({"fulfillmentText": "Sorry, I didn't catch that. Please rephrase."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
