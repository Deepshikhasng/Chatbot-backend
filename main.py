from flask import Flask, request, jsonify
from fuzzywuzzy import process

app = Flask(__name__)

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
    intent = req['queryResult']['intent']['displayName']
    user_query = req['queryResult']['queryText'].lower()

    # Default Welcome Intent – Send chip buttons
    if intent == "Default Welcome Intent":
        return jsonify({
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": ["Hi! How can I assist you today?"]
                    }
                },
                {
                    "payload": {
                        "richContent": [
                            [
                                {
                                    "type": "chips",
                                    "options": [
                                        {"text": "Basic Questions"},
                                        {"text": "Service-related Questions"},
                                        {"text": "Data Centre"}
                                    ]
                                }
                            ]
                        ]
                    }
                }
            ]
        })

    # Handle chip response: Basic Questions
    if user_query == "basic questions":
        return jsonify({
            "fulfillmentText": "Sure! Feel free to ask anything about our company or general topics. I'm here to help!"
        })

    # Handle chip response: Service-related Questions → Show Hyperscaler & Traditional IaaS
    if user_query == "service-related questions":
        return jsonify({
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": ["We provide these service types. Select one:"]
                    }
                },
                {
                    "payload": {
                        "richContent": [
                            [
                                {
                                    "type": "chips",
                                    "options": [
                                        {"text": "Hyperscaler"},
                                        {"text": "Traditional IaaS"}
                                    ]
                                }
                            ]
                        ]
                    }
                }
            ]
        })

    # Handle Hyperscaler → Show 4 cloud platform buttons
    if user_query == "hyperscaler":
        return jsonify({
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": ["Explore our cloud providers:"]
                    }
                },
                {
                    "payload": {
                        "richContent": [
                            [
                                {
                                    "type": "button",
                                    "icon": {"type": "cloud"},
                                    "text": "AWS",
                                    "link": "https://upgraded-lamp-g47qqww45p99fpvqv-5500.app.github.dev/newer_index_testng.html#aws"
                                },
                                {
                                    "type": "button",
                                    "icon": {"type": "cloud"},
                                    "text": "Azure",
                                    "link": "https://upgraded-lamp-g47qqww45p99fpvqv-5500.app.github.dev/newer_index_testng.html#azure"
                                },
                                {
                                    "type": "button",
                                    "icon": {"type": "cloud"},
                                    "text": "Oracle",
                                    "link": "https://upgraded-lamp-g47qqww45p99fpvqv-5500.app.github.dev/newer_index_testng.html#oracle"
                                },
                                {
                                    "type": "button",
                                    "icon": {"type": "cloud"},
                                    "text": "Google Cloud",
                                    "link": "https://upgraded-lamp-g47qqww45p99fpvqv-5500.app.github.dev/newer_index_testng.html#googlecloud"
                                }
                            ]
                        ]
                    }
                }
            ]
        })

    # Handle Traditional IaaS → Show Yotta and Sify buttons
    if user_query == "traditional iaas":
        return jsonify({
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": ["Explore our Traditional IaaS providers:"]
                    }
                },
                {
                    "payload": {
                        "richContent": [
                            [
                                {
                                    "type": "button",
                                    "icon": {"type": "storage"},
                                    "text": "Yotta",
                                    "link": "https://upgraded-lamp-g47qqww45p99fpvqv-5500.app.github.dev/newer_index_testng.html#yotta"
                                },
                                {
                                    "type": "button",
                                    "icon": {"type": "storage"},
                                    "text": "Sify",
                                    "link": "https://upgraded-lamp-g47qqww45p99fpvqv-5500.app.github.dev/newer_index_testng.html#sify"
                                }
                            ]
                        ]
                    }
                }
            ]
        })

    # Fuzzy match user queries with known FAQ entries
    best_match, score = process.extractOne(user_query, faq.keys())
    if score >= 70:
        response = faq[best_match]
    else:
        response = "Sorry, I didn't quite catch that. Could you please rephrase?"

    return jsonify({"fulfillmentText": response})

# Run the Flask app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
