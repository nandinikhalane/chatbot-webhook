from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, your webhook is live on Render! 🎉"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True)
    print("Received from Dialogflow:", data)  # log incoming request
    
    response = {
        "fulfillmentText": "This is a test response from webhook!"
    }
    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
