from flask import Flask, request, jsonify
from fuzzywuzzy import process
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

app = Flask(__name__)

user_details = {}

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds_raw = os.environ.get("GOOGLE_CREDENTIALS_JSON")
if not google_creds_raw:
    raise Exception("Google Credentials not found.")

google_creds_dict = json.loads(google_creds_raw)
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("chatbot_userdata").sheet1

faq = {
    "can i upgrade or downgrade my plan": "Yes, flexible plans allow easy upgrades.",
    "what is cloud hosting": "Cloud hosting offers scalable virtual servers.",
    "do you offer technical support": "Yes, 24/7 technical support is available.",
    "what are your service hours": "Our services operate 24/7, including holidays.",
    "how can i cancel my subscription": "Cancel via dashboard or by contacting support.",
    "do you offer custom plans": "Yes, contact sales for customized plans."
}

@app.route('/')
def index():
    return 'Webhook server running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json()
    intent = req.get('queryResult', {}).get('intent', {}).get('displayName', "")
    user_query = req.get('queryResult', {}).get('queryText', "").lower()
    session = req.get('session', "")

    if session not in user_details:
        user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": "", "dcdr_choice": ""}

    step = user_details[session]["step"]

    # Initial Greeting
    if intent == "Default Welcome Intent":
        user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": "", "dcdr_choice": ""}
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Hi! What would you like to ask about?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [
                        {"text": "Basic FAQ"},
                        {"text": "Service Available"}
                    ]}
                ]]} }
            ]
        })

    # Basic FAQ flow
    if user_query == "basic faq":
        return jsonify({"fulfillmentText": "Sure! Feel free to ask any general question about our services."})

    # Service Available options
    if user_query == "service available":
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Select a service to explore:"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [
                        {"text": "Data Centre"},
                        {"text": "Cloud"},
                        {"text": "Dedicated Server"},
                        {"text": "Co-location"}
                    ]}
                ]]} }
            ]
        })

    # Data Centre: Capture Name, Contact, Email
    if user_query == "data centre":
        user_details[session]["step"] = "ask_name"
        return jsonify({"fulfillmentText": "Great! Please share your Name."})

    if step == "ask_name":
        user_details[session]["name"] = user_query.title()
        user_details[session]["step"] = "ask_contact"
        return jsonify({"fulfillmentText": "Thank you! Please enter your 10-digit Contact Number."})

    if step == "ask_contact":
        if not user_query.isdigit() or len(user_query) != 10:
            return jsonify({"fulfillmentText": "❗ Please enter a valid 10-digit Contact Number."})
        user_details[session]["contact"] = user_query
        user_details[session]["step"] = "ask_email"
        return jsonify({"fulfillmentText": "Almost done! Please enter your Email address."})

    if step == "ask_email":
        user_details[session]["email"] = user_query
        collected = user_details[session]
        try:
            sheet.append_row([collected["name"], collected["contact"], collected["email"]])
        except Exception as e:
            print(f"Sheet Error: {e}")
        user_details[session]["step"] = "ask_solution_type"
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Are you interested in On-Premises or Cloud solutions?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [
                        {"text": "On-Premises"},
                        {"text": "Cloud"}
                    ]}
                ]]} }
            ]
        })

    # On-Premises or Cloud branching
    if step == "ask_solution_type":
        if user_query.lower() == "on-premises":
            user_details[session]["solution_type"] = "On-Premises"
            user_details[session]["step"] = "ask_onprem_status"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Are you a New or Existing customer?"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [
                            {"text": "New"},
                            {"text": "Existing"}
                        ]}
                    ]]} }
                ]
            })
        if user_query.lower() == "cloud":
            user_details[session]["solution_type"] = "Cloud"
            user_details[session]["step"] = "ask_cloud_dcdr"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Please choose an option:"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [
                            {"text": "DC"},
                            {"text": "DR"},
                            {"text": "Both"}
                        ]}
                    ]]} }
                ]
            })

    # On-Premises New/Existing
    if step == "ask_onprem_status":
        if user_query.lower() == "new":
            user_details[session]["step"] = "ask_onprem_dcdr"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Please choose an option:"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [
                            {"text": "DC"},
                            {"text": "DR"},
                            {"text": "Both"}
                        ]}
                    ]]} }
                ]
            })
        if user_query.lower() == "existing":
            user_details[session]["step"] = "ask_onprem_existing_req"
            return jsonify({"fulfillmentText": "Kindly explain your requirements for Existing On-Premises customer."})

    if step == "ask_onprem_dcdr":
        if user_query.lower() in ["dc", "dr", "both"]:
            solution = user_details[session]["solution_type"]
            user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": "", "dcdr_choice": ""}
            return jsonify({"fulfillmentText": f"Thank you for choosing {solution} with {user_query.upper()} services. Our team will contact you shortly."})

    if step == "ask_onprem_existing_req":
        try:
            sheet.append_row([user_details[session]["name"], user_details[session]["contact"], user_details[session]["email"], user_query, "Existing On-Premises"])
        except Exception as e:
            print(f"Sheet Error: {e}")
        user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": "", "dcdr_choice": ""}
        return jsonify({"fulfillmentText": "Thank you for sharing your requirements. Our team will contact you shortly."})

    # Cloud DC/DR/Both flow
    if step == "ask_cloud_dcdr":
        if user_query.lower() in ["dc", "dr", "both"]:
            user_details[session]["dcdr_choice"] = user_query.upper()
            user_details[session]["step"] = "ask_cloud_type"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Choose a service type:"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [
                            {"text": "Hyperscaler"},
                            {"text": "Traditional IaaS"}
                        ]}
                    ]]} }
                ]
            })

    if step == "ask_cloud_type":
        if user_query.lower() == "hyperscaler":
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Select a Cloud provider:"]}},
                    {"payload": {"richContent": [[
                        {"type": "button", "icon": {"type": "cloud"}, "text": "AWS", "link": "https://example.com/aws"},
                        {"type": "button", "icon": {"type": "cloud"}, "text": "Azure", "link": "https://example.com/azure"},
                        {"type": "button", "icon": {"type": "cloud"}, "text": "Google Cloud", "link": "https://example.com/google"},
                        {"type": "button", "icon": {"type": "cloud"}, "text": "Oracle", "link": "https://example.com/oracle"}
                    ]]} }
                ]
            })
        if user_query.lower() == "traditional iaas":
            user_details[session]["step"] = "ask_traditional_req"
            return jsonify({"fulfillmentText": "Kindly explain your requirement for Traditional IaaS."})

    if step == "ask_traditional_req":
        try:
            sheet.append_row([user_details[session]["name"], user_details[session]["contact"], user_details[session]["email"], user_query, "Traditional IaaS Requirement"])
        except Exception as e:
            print(f"Sheet Error: {e}")
        user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": "", "dcdr_choice": ""}
        return jsonify({"fulfillmentText": "Thank you for sharing your requirement. Our team will contact you shortly."})

    # Co-location placeholders
    if user_query == "co-location":
        user_details[session]["step"] = "ask_colocation_status"
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Are you a New or Existing Co-location customer?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [
                        {"text": "New"},
                        {"text": "Existing"}
                    ]}
                ]]} }
            ]
        })

    if step == "ask_colocation_status":
        if user_query.lower() == "new":
            return jsonify({"fulfillmentText": "New Co-location functionality coming soon."})
        if user_query.lower() == "existing":
            return jsonify({"fulfillmentText": "Existing Co-location functionality coming soon."})

    # Fallback for FAQ
    if faq:
        best_match, score = process.extractOne(user_query, faq.keys())
        if score >= 70:
            return jsonify({"fulfillmentText": faq[best_match]})
        else:
            return jsonify({"fulfillmentText": "Sorry, I didn't understand that. Please rephrase."})

    return jsonify({"fulfillmentText": "I'm not sure how to help with that."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
