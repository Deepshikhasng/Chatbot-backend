from flask import Flask, request, jsonify
from fuzzywuzzy import process
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

app = Flask(__name__)

user_details = {}

# Google Sheets Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CRED_PATH = os.path.join(BASE_DIR, "credentials", "chatbotuserdata-93b488d01c56.json")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CRED_PATH, scope)
client = gspread.authorize(creds)
  # Replace your JSON file name
client = gspread.authorize(creds)
sheet = client.open("chatbot_userdata").sheet1  # Replace with your Google Sheet name

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
        user_details[session] = {"step": "", "name": "", "contact": "", "email": ""}

    step = user_details[session]["step"]

    # Default Welcome Intent
    if intent == "Default Welcome Intent":
        user_details[session] = {"step": "", "name": "", "contact": "", "email": ""}
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

    # Basic Questions
    if user_query == "basic questions":
        return jsonify({"fulfillmentText": "Sure! Feel free to ask anything about our company or general topics."})

    # Co-location
    if user_query == "co-location":
        return jsonify({"fulfillmentText": "You have selected Co-location. Kindly share your query related to Co-location, and I will be happy to assist you."})

    # Service-related Questions
    if user_query == "service-related questions":
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["We provide these service types. Select one:"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [{"text": "Hyperscaler"}, {"text": "Traditional IaaS"}]}
                ]]}}
            ]
        })

    # Hyperscaler
    if user_query == "hyperscaler":
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["These are our services:"]}},
                {"payload": {"richContent": [[
                    {"type": "button", "icon": {"type": "cloud"}, "text": "AWS", "link": "https://upgraded-lamp-g47qqww45p99fpvqv-5500.app.github.dev/newer_index_testng.html#aws"},
                    {"type": "button", "icon": {"type": "cloud"}, "text": "Azure", "link": "https://upgraded-lamp-g47qqww45p99fpvqv-5500.app.github.dev/newer_index_testng.html#azure"},
                    {"type": "button", "icon": {"type": "cloud"}, "text": "Oracle", "link": "https://upgraded-lamp-g47qqww45p99fpvqv-5500.app.github.dev/newer_index_testng.html#oracle"},
                    {"type": "button", "icon": {"type": "cloud"}, "text": "Google Cloud", "link": "https://upgraded-lamp-g47qqww45p99fpvqv-5500.app.github.dev/newer_index_testng.html#googlecloud"}
                ]]}}
            ],
            "outputContexts": [{"name": f"{session}/contexts/end_session", "lifespanCount": 0}]
        })

    # Traditional IaaS
    if user_query == "traditional iaas":
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["These are our services:"]}},
                {"payload": {"richContent": [[
                    {"type": "button", "icon": {"type": "storage"}, "text": "Yotta", "link": "https://upgraded-lamp-g47qqww45p99fpvqv-5500.app.github.dev/newer_index_testng.html#yotta"},
                    {"type": "button", "icon": {"type": "storage"}, "text": "Sify", "link": "https://upgraded-lamp-g47qqww45p99fpvqv-5500.app.github.dev/newer_index_testng.html#sify"}
                ]]}}
            ],
            "outputContexts": [{"name": f"{session}/contexts/end_session", "lifespanCount": 0}]
        })

    # Data Centre Flow
    if user_query == "data centre":
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": ["A Data Centre is a facility that centralizes IT operations for managing and storing data."]}},
                {"text": {"text": ["Would you like to continue exploring Data Centre services?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [{"text": "Yes"}, {"text": "No"}]}
                ]]}}
            ]
        })

    if user_query == "no":
        user_details[session] = {"step": "", "name": "", "contact": "", "email": ""}
        return jsonify({
            "fulfillmentText": "Thank you for your time! You can restart the chat anytime by typing Hi or Restart.",
            "outputContexts": [{"name": f"{session}/contexts/end_session", "lifespanCount": 0}]
        })

    if user_query == "yes":
        user_details[session]["step"] = "ask_name"
        return jsonify({"fulfillmentText": "Great! Please share your Name."})

    if step == "ask_name":
        user_details[session]["name"] = user_query
        user_details[session]["step"] = "ask_contact"
        return jsonify({"fulfillmentText": "Thanks! Now please share your Contact Number."})

    if step == "ask_contact":
        user_details[session]["contact"] = user_query
        user_details[session]["step"] = "ask_email"
        return jsonify({"fulfillmentText": "Got it! Finally, please share your Email address."})

    if step == "ask_email":
        user_details[session]["email"] = user_query
        collected = user_details[session]

        # Store in Google Sheet
        try:
            sheet.append_row([collected["name"], collected["contact"], collected["email"]])
        except Exception as e:
            print(f"Error storing to sheet: {e}")

        user_details[session]["step"] = "done"
        return jsonify({
            "fulfillmentMessages": [
                {"text": {"text": [f"Thank you {collected['name']}! We have your details:\nContact: {collected['contact']}\nEmail: {collected['email']}"]}},
                {"text": {"text": ["Are you a New customer or Existing one?"]}},
                {"payload": {"richContent": [[
                    {"type": "chips", "options": [{"text": "New"}, {"text": "Existing"}]}
                ]]}}
            ]
        })

    if user_query == "new":
        user_details[session] = {"step": "", "name": "", "contact": "", "email": ""}
        return jsonify({"fulfillmentText": "Thank you! Our team will assist you as a new customer shortly."})

    if user_query == "existing":
        user_details[session] = {"step": "", "name": "", "contact": "", "email": ""}
        return jsonify({"fulfillmentText": "Thank you! Our support team will assist you shortly as an existing customer."})

    # Fuzzy matching for FAQ
    if faq:
        best_match, score = process.extractOne(user_query, faq.keys())
        if score >= 70:
            return jsonify({"fulfillmentText": faq[best_match]})
        else:
            return jsonify({"fulfillmentText": "Sorry, I didn't quite catch that. Could you please rephrase?"})

    return jsonify({"fulfillmentText": "I'm not sure how to help with that. Please try again."})

# Run Flask
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
