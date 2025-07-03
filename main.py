from flask import Flask, request, jsonify
from fuzzywuzzy import process
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

app = Flask(__name__)

user_details = {}

# Google Sheets Setup using Environment Variable
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
    "can i upgrade or downgrade my plan": "Yes, our flexible plans allow you to easily upgrade your services at any time.",
    "what is cloud hosting": "Cloud hosting uses a network of virtual servers hosted on the internet, offering scalable resources and higher uptime compared to traditional hosting.",
    "do you offer technical support": "Yes, our team offers 24/7 technical support through multiple channels.",
    "what are your service hours": "Our services are available 24/7, including holidays.",
    "how can i cancel my subscription": "You can cancel your subscription through your dashboard or by contacting support.",
    "do you offer custom plans": "Yes, we offer customized plans tailored to your business needs. Contact our sales team for more details."
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
        user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": ""}

    step = user_details[session]["step"]

    if intent == "Default Welcome Intent":
        user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": ""}
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Hi! What would you like to ask about?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [
                        {"text": "Basic FAQs"},
                        {"text": "Service Available"}
                    ]}
                ]]}}
            ]
        })

    if user_query == "basic faqs":
        return jsonify({"fulfillmentText": "Sure! You can ask any general questions about our services."})

    if user_query == "service available":
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["We offer the following services, select one:"]}},
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

    if user_query == "data centre":
        user_details[session]["step"] = "ask_name"
        return jsonify({"fulfillmentText": "Great! Please share your Name."})

    if step == "ask_name":
        user_details[session]["name"] = user_query.title()
        user_details[session]["step"] = "ask_contact"
        return jsonify({"fulfillmentText": "Thank you! Now, please enter your 10-digit Contact Number."})

    if step == "ask_contact":
        if not user_query.isdigit() or len(user_query) != 10:
            return jsonify({"fulfillmentText": "❗ Please enter a valid 10-digit Contact Number."})
        user_details[session]["contact"] = user_query
        user_details[session]["step"] = "ask_email"
        return jsonify({"fulfillmentText": "Almost done! Please enter your Email address."})

    if step == "ask_email":
        user_details[session]["email"] = user_query
        try:
            sheet.append_row([
                user_details[session]["name"],
                user_details[session]["contact"],
                user_details[session]["email"]
            ])
        except Exception as e:
            print(f"Error storing to sheet: {e}")
        user_details[session]["step"] = "ask_solution"
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Thank you! Are you interested in On-Premises or On-Cloud?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [
                        {"text": "On-Premises"},
                        {"text": "On-Cloud"}
                    ]}
                ]]}}
            ]
        })

    if step == "ask_solution":
        if user_query == "on-premises":
            user_details[session]["step"] = "onprem_new_existing"
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

        if user_query == "on-cloud":
            user_details[session]["step"] = "cloud_dc_dr"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Please select one option:"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [
                            {"text": "DC"},
                            {"text": "DR"},
                            {"text": "Both"}
                        ]}
                    ]]}}
                ]
            })

    if step == "onprem_new_existing":
        if user_query == "new":
            user_details[session]["step"] = "onprem_new_options"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Please select DC, DR, Both, or Back:"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [
                            {"text": "DC"},
                            {"text": "DR"},
                            {"text": "Both"},
                            {"text": "Back"}
                        ]}
                    ]]}}
                ]
            })

        if user_query == "existing":
            user_details[session]["step"] = "existing_requirement"
            return jsonify({"fulfillmentText": "Kindly explain your requirements."})

    if step == "existing_requirement":
        try:
            sheet.append_row([
                user_details[session]["name"],
                user_details[session]["contact"],
                user_details[session]["email"],
                "Requirement of existing user",
                user_query
            ])
        except Exception as e:
            print(f"Error storing to sheet: {e}")
        user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": ""}
        return jsonify({"fulfillmentText": "Thank you! Our team will contact you shortly."})

    if step == "onprem_new_options":
        if user_query.lower() in ["dc", "dr", "both"]:
            return jsonify({"fulfillmentText": f"Thank you for choosing {user_query.upper()} services. Our team will contact you shortly."})
        if user_query.lower() == "back":
            user_details[session]["step"] = "onprem_new_existing"
            return jsonify({"fulfillmentText": "Are you a New or Existing customer?"})

    if step == "cloud_dc_dr":
        if user_query.lower() in ["dc", "dr", "both"]:
            user_details[session]["step"] = "cloud_service_type"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Please choose service type:"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [
                            {"text": "Hyperscaler"},
                            {"text": "Traditional IAAS"}
                        ]}
                    ]]}}
                ]
            })

    if step == "cloud_service_type":
        if user_query.lower() == "hyperscaler":
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Select your provider:"]}},
                    {"payload": {"richContent": [[
                        {"type": "button", "icon": {"type": "cloud"}, "text": "AWS", "link": "https://example.com/aws"},
                        {"type": "button", "icon": {"type": "cloud"}, "text": "Azure", "link": "https://example.com/azure"},
                        {"type": "button", "icon": {"type": "cloud"}, "text": "Google Cloud", "link": "https://example.com/googlecloud"},
                        {"type": "button", "icon": {"type": "cloud"}, "text": "Oracle", "link": "https://example.com/oracle"}
                    ]]}}
                ]
            })

        if user_query.lower() == "traditional iaas":
            user_details[session]["step"] = "trad_iaas_req"
            return jsonify({"fulfillmentText": "Kindly explain your requirement for Traditional IAAS."})

    if step == "trad_iaas_req":
        try:
            sheet.append_row([
                user_details[session]["name"],
                user_details[session]["contact"],
                user_details[session]["email"],
                "Requirement of Traditional IAAS",
                user_query
            ])
        except Exception as e:
            print(f"Error storing to sheet: {e}")
        return jsonify({"fulfillmentText": "Thank you! Our team will contact you shortly."})

    return jsonify({"fulfillmentText": "I'm not sure how to help with that. Please try again."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
