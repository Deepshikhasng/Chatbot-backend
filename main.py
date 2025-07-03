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
        user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": "", "customer_type": ""}

    step = user_details[session]["step"]

    if intent == "Default Welcome Intent":
        user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": "", "customer_type": ""}
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Hi! What would you like to ask about?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [
                        {"text": "Basic FAQs"},
                        {"text": "Service Available"}
                    ]}
                ]]} }
            ]
        })

    # Basic FAQs flow
    if user_query == "basic faqs":
        return jsonify({"fulfillmentText": "Sure! Feel free to ask anything from our Frequently Asked Questions."})

    # Service Available flow
    if user_query == "service available":
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["We offer the following services, select one:"]}},
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

    # Data Centre Flow
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
        collected = user_details[session]

        try:
            sheet.append_row([collected["name"], collected["contact"], collected["email"]])
        except Exception as e:
            print(f"Error storing to sheet: {e}")

        user_details[session]["step"] = "ask_solution_type"
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": [f"Thank you {collected['name']}! Your details have been recorded."]}},
                {"text": {"text": ["Are you interested in On-Premises or On-Cloud solutions?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [
                        {"text": "On-Premises"},
                        {"text": "On-Cloud"}
                    ]}
                ]]} }
            ]
        })

    if step == "ask_solution_type":
        if user_query.lower() == "on-premises":
            user_details[session]["solution_type"] = "On-Premises"
            user_details[session]["step"] = "ask_customer_type"
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
        elif user_query.lower() == "on-cloud":
            user_details[session]["solution_type"] = "On-Cloud"
            return jsonify({"fulfillmentText": "Cloud redirection will be added soon."})

    if step == "ask_customer_type":
        if user_query.lower() == "new":
            user_details[session]["step"] = "ask_dc_dr"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Please select your requirement:"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [
                            {"text": "DC"},
                            {"text": "DR"},
                            {"text": "Both"},
                            {"text": "Back"}
                        ]}
                    ]]} }
                ]
            })
        elif user_query.lower() == "existing":
            user_details[session]["step"] = "ask_existing_req"
            return jsonify({"fulfillmentText": "Kindly explain your requirements for our team to assist you."})

    if step == "ask_dc_dr":
        if user_query.lower() in ["dc", "dr", "both"]:
            user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": "", "customer_type": ""}
            return jsonify({"fulfillmentText": f"Thank you for choosing {user_query.upper()} services. Our team will contact you shortly."})
        if user_query.lower() == "back":
            user_details[session]["step"] = "ask_customer_type"
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

    if step == "ask_existing_req":
        try:
            sheet.append_row(["Existing Customer Requirement", user_query])
        except Exception as e:
            print(f"Error storing requirement: {e}")
        user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": "", "customer_type": ""}
        return jsonify({"fulfillmentText": "Thank you! Your requirement has been noted. Our team will contact you shortly."})

    # Cloud option under "Service Available" (empty for now)
    if user_query == "cloud":
        return jsonify({"fulfillmentText": "Cloud option selected. Redirection will be added shortly."})

    if user_query == "dedicated server":
        return jsonify({"fulfillmentText": "You selected Dedicated Server. Kindly share your requirements."})

    if user_query == "co-location":
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

    # FAQ fallback if no specific flow is ongoing
    if not step and faq:
        best_match, score = process.extractOne(user_query, faq.keys())
        if score >= 70:
            return jsonify({"fulfillmentText": faq[best_match]})
        else:
            return jsonify({"fulfillmentText": "Sorry, I didn't quite catch that. Could you please rephrase?"})

    return jsonify({"fulfillmentText": "I'm not sure how to help with that. Please try again."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
