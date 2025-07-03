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
    "can i upgrade or downgrade my plan": "Yes, you can upgrade or downgrade your services anytime.",
    "what is cloud hosting": "Cloud hosting provides scalable resources via virtual servers on the internet.",
    "do you offer technical support": "Yes, 24/7 technical support is available.",
    "what are your service hours": "Our services run 24/7 including holidays.",
    "how can i cancel my subscription": "You can cancel anytime via dashboard or support.",
    "do you offer custom plans": "Yes, contact our sales team for tailored solutions."
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
        user_details[session] = {"step": "ask_name", "name": "", "contact": "", "email": "", "solution_type": ""}

    step = user_details[session]["step"]

    # Greeting and Collect User Info First
    if intent == "Default Welcome Intent":
        user_details[session] = {"step": "ask_name", "name": "", "contact": "", "email": "", "solution_type": ""}
        return jsonify({"fulfillmentText": "Hi! Welcome to our services. Please share your Name."})

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
            print(f"Error storing user details: {e}")
        user_details[session]["step"] = "main_menu"
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Thank you! What would you like to ask about?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [
                        {"text": "Basic FAQ"},
                        {"text": "Service Available"}
                    ]}
                ]]}}
            ]
        })

    # Main Menu Options
    if step == "main_menu":
        if user_query == "basic faq":
            return jsonify({"fulfillmentText": "Sure! Feel free to ask anything from our FAQs."})

        if user_query == "service available":
            user_details[session]["step"] = "service_options"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["These are our available services:"]}},
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
            user_details[session]["step"] = "ask_solution_dc"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Are you interested in On-Premises or Cloud Services?"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [
                            {"text": "On-Premises"},
                            {"text": "Cloud Services"}
                        ]}
                    ]]}}
                ]
            })
        if user_query == "cloud services":
            user_details[session]["step"] = "cloud_dc_dr"
            return cloud_dc_dr_buttons()
        if user_query == "dedicated server":
            return jsonify({"fulfillmentText": "Dedicated Server details coming soon."})
        if user_query == "co-location":
            return jsonify({"fulfillmentText": "Co-location options coming soon."})

    # On-Premises after Data Centre
    if step == "ask_solution_dc":
        if user_query == "on-premises":
            user_details[session]["step"] = "ask_new_existing"
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
        if user_query == "cloud services":
            user_details[session]["step"] = "cloud_dc_dr"
            return cloud_dc_dr_buttons()

    if step == "ask_new_existing":
        if user_query == "new":
            user_details[session]["step"] = "ask_dc_dr"
            return dc_dr_buttons()
        if user_query == "existing":
            user_details[session]["step"] = "ask_existing_req"
            return jsonify({"fulfillmentText": "Kindly explain your requirements."})

    if step == "ask_existing_req":
        try:
            sheet.append_row(["Existing User Requirement", user_query])
        except Exception as e:
            print(f"Error storing requirement: {e}")
        user_details[session]["step"] = "main_menu"
        return jsonify({"fulfillmentText": "Thank you! Our team will contact you shortly."})

    if step == "ask_dc_dr":
        if user_query.lower() in ["dc", "dr", "both"]:
            user_details[session]["step"] = "main_menu"
            return jsonify({"fulfillmentText": f"Thank you for choosing {user_query.upper()} services. Our team will contact you shortly."})

    # Cloud Button (Common Flow)
    if step == "cloud_dc_dr":
        if user_query.lower() in ["dc", "dr", "both"]:
            user_details[session]["step"] = "cloud_type_choice"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Choose one:"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [
                            {"text": "Hyperscaler"},
                            {"text": "Traditional IAAS"}
                        ]}
                    ]]}}
                ]
            })

    if step == "cloud_type_choice":
        if user_query.lower() == "hyperscaler":
            user_details[session]["step"] = "main_menu"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Select a Cloud Provider:"]}},
                    {"payload": {"richContent": [[
                        {"type": "button", "text": "AWS", "link": "https://example.com/aws"},
                        {"type": "button", "text": "Azure", "link": "https://example.com/azure"},
                        {"type": "button", "text": "Google Cloud", "link": "https://example.com/googlecloud"},
                        {"type": "button", "text": "Oracle", "link": "https://example.com/oracle"}
                    ]]}}
                ]
            })
        if user_query.lower() == "traditional iaas":
            user_details[session]["step"] = "ask_traditional_req"
            return jsonify({"fulfillmentText": "Kindly explain your requirement for Traditional IAAS."})

    if step == "ask_traditional_req":
        try:
            sheet.append_row(["Requirement Traditional IAAS", user_query])
        except Exception as e:
            print(f"Error storing Traditional IAAS requirement: {e}")
        user_details[session]["step"] = "main_menu"
        return jsonify({"fulfillmentText": "Thank you! Our team will contact you shortly."})

    # Basic FAQ Fallback
    if faq and step == "main_menu":
        best_match, score = process.extractOne(user_query, faq.keys())
        if score >= 70:
            return jsonify({"fulfillmentText": faq[best_match]})

    return jsonify({"fulfillmentText": "I'm not sure how to help with that. Please try again."})

# Helpers for button responses
def cloud_dc_dr_buttons():
    return jsonify({
        "fulfillmentMessages": [
            {"text": {"text": ["Please select an option:"]}},
            {"payload": {"richContent": [[
                {"type": "chips", "options": [
                    {"text": "DC"},
                    {"text": "DR"},
                    {"text": "Both"}
                ]}
            ]]}}
        ]
    })

def dc_dr_buttons():
    return jsonify({
        "fulfillmentMessages": [
            {"text": {"text": ["Please select an option:"]}},
            {"payload": {"richContent": [[
                {"type": "chips", "options": [
                    {"text": "DC"},
                    {"text": "DR"},
                    {"text": "Both"}
                ]}
            ]]}}
        ]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
