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

faq = {
    "can i upgrade or downgrade my plan": "Yes, you can upgrade anytime.",
    "what is cloud hosting": "Cloud hosting offers scalable resources.",
    "do you offer technical support": "Yes, 24/7 technical support is available.",
    "what are your service hours": "Our services are available 24/7.",
    "how can i cancel my subscription": "You can cancel via dashboard or support.",
    "do you offer custom plans": "Yes, we offer tailored plans. Contact sales."
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
                {"text": {"text": ["Hi! How can I assist you today?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [
                        {"text": "Basic Questions"},
                        {"text": "Service-related Questions"},
                        {"text": "Data Centre"},
                        {"text": "Co-location"}
                    ]}
                ]]}}
            ]
        })

    if user_query == "basic questions":
        return jsonify({"fulfillmentText": "Feel free to ask anything about our company or services."})

    if user_query == "co-location":
        return jsonify({"fulfillmentText": "You selected Co-location. Please share your query."})

    if user_query == "service-related questions":
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Select a service type:"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [{"text": "Hyperscaler"}, {"text": "Traditional IaaS"}]}
                ]]}}
            ]
        })

    if user_query == "hyperscaler":
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Our Hyperscaler services:"]}},
                {"payload": {"richContent": [[
                    {"type": "button", "icon": {"type": "cloud"}, "text": "AWS", "link": "https://example.com/aws"},
                    {"type": "button", "icon": {"type": "cloud"}, "text": "Azure", "link": "https://example.com/azure"},
                    {"type": "button", "icon": {"type": "cloud"}, "text": "Oracle", "link": "https://example.com/oracle"},
                    {"type": "button", "icon": {"type": "cloud"}, "text": "Google Cloud", "link": "https://example.com/googlecloud"}
                ]]}}
            ],
            "outputContexts": [{"name": f"{session}/contexts/end_session", "lifespanCount": 0}]
        })

    if user_query == "traditional iaas":
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["Our Traditional IaaS services:"]}},
                {"payload": {"richContent": [[
                    {"type": "button", "icon": {"type": "storage"}, "text": "Yotta", "link": "https://example.com/yotta"},
                    {"type": "button", "icon": {"type": "storage"}, "text": "Sify", "link": "https://example.com/sify"}
                ]]}}
            ],
            "outputContexts": [{"name": f"{session}/contexts/end_session", "lifespanCount": 0}]
        })

    if user_query == "data centre":
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["A Data Centre centralizes IT operations for managing and storing data."]}},
                {"text": {"text": ["Would you like to continue exploring Data Centre services?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [{"text": "Yes"}, {"text": "No"}]}
                ]]}}
            ]
        })

    if user_query == "no":
        user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": ""}
        return jsonify({"fulfillmentText": "Thank you! Restart anytime by typing Hi."})

    if user_query == "yes":
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

        user_details[session]["step"] = "ask_customer_type"
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": [f"Thank you {collected['name']}! Your details are saved."]}},
                {"text": {"text": ["Are you a New customer or Existing customer?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [{"text": "New"}, {"text": "Existing"}]}
                ]]}}
            ]
        })

    if step == "ask_customer_type":
        if user_query.lower() == "new":
            user_details[session]["step"] = "ask_solution_type"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": ["Are you interested in On-Premises or Cloud solutions?"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [{"text": "On-Premises"}, {"text": "Cloud"}]}
                    ]]}}
                ]
            })
        elif user_query.lower() == "existing":
            user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": ""}
            return jsonify({"fulfillmentText": "Thank you! Our support team will assist you shortly."})

    if step == "ask_solution_type":
        if user_query.lower() in ["on-premises", "cloud"]:
            user_details[session]["solution_type"] = user_query.capitalize()
            user_details[session]["step"] = "ask_service"
            return jsonify({
                "fulfillmentMessages": [
                    {"text": {"text": [f"You selected {user_query.capitalize()}. Please choose an option:"]}},
                    {"payload": {"richContent": [[
                        {"type": "chips", "options": [{"text": "DC"}, {"text": "DR"}, {"text": "Both"}]}
                    ]]}}
                ]
            })

    if step == "ask_service":
        if user_query.lower() in ["dc", "dr", "both"]:
            solution = user_details[session]["solution_type"]
            user_details[session] = {"step": "", "name": "", "contact": "", "email": "", "solution_type": ""}
            return jsonify({"fulfillmentText": f"Thank you for choosing {solution} with {user_query.upper()} services. Our team will contact you shortly."})

    # Fuzzy Matching for FAQ
    if not step and faq:
        best_match, score = process.extractOne(user_query, faq.keys())
        if score >= 70:
            return jsonify({"fulfillmentText": faq[best_match]})
        else:
            return jsonify({"fulfillmentText": "Sorry, I didn't catch that. Please rephrase."})

    return jsonify({"fulfillmentText": "I'm not sure how to help with that. Please try again."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
