from flask import Flask, request, jsonify

app = Flask(__name__)

# Crisis helpline constant
TELE_MANAS_HELPLINE = "14416"

# -----------------------
# Utility: build response
# -----------------------
def text_response(text):
    return {
        "fulfillmentMessages": [
            {"text": {"text": [text]}}
        ]
    }

# -----------------------
# Intent Handlers
# -----------------------
def handle_welcome():
    return text_response("Hi! I’m glad you reached out. How are you feeling today?")

def handle_thanks():
    return text_response("You’re welcome! I’m here whenever you want to talk.")

def handle_goodbye():
    return text_response("Take care! Reach out anytime. You are not alone.")

def handle_share_problem(parameters):
    problem_type = parameters.get("problem_type")
    if problem_type:
        return text_response(
            f"I hear you… it sounds like {problem_type} has been tough for you. "
            "Would you like me to ask a few short questions (PHQ-9 or GAD-7) "
            "that professionals often use to check mood and stress?"
        )
    return text_response(
        "Thanks for sharing. Would you like me to ask you a short screening questionnaire "
        "that helps many people understand how they’re feeling?"
    )

def handle_offer_screening():
    return text_response(
        "I can ask a few short questions used by professionals. "
        "It takes about 2–3 minutes. Is it okay if I ask them?"
    )

# -----------------------
# PHQ-9 Example (Q1 → Q9)
# -----------------------
def handle_phq9(parameters):
    # Collect all answers
    score = 0
    for i in range(1, 10):  # phq9_q1 ... phq9_q9
        ans = parameters.get(f"phq9_q{i}")
        if ans is not None:
            try:
                score += int(ans)
            except ValueError:
                pass

    # Interpret score safely
    if score <= 4:
        feedback = "Your responses suggest minimal symptoms. Self-care and healthy routines can help."
    elif score <= 9:
        feedback = "Your responses suggest mild symptoms. Talking to a counselor could be useful."
    elif score <= 14:
        feedback = "Your responses suggest moderate symptoms. Seeking help from a mental health professional is recommended."
    elif score <= 19:
        feedback = "Your responses suggest moderately severe symptoms. Please consider professional support soon."
    else:
        feedback = (
            "Your responses suggest severe symptoms. "
            f"If you are in crisis, please call Tele-MANAS helpline at {TELE_MANAS_HELPLINE} "
            "or your local emergency number immediately."
        )

    return text_response(
        f"Thanks for completing the questionnaire. Your total PHQ-9 score is {score}. {feedback}"
    )

# -----------------------
# Crisis Handling
# -----------------------
def handle_crisis():
    return text_response(
        f"I’m really concerned about your safety. If you are in immediate danger, "
        f"please call the Tele-MANAS helpline at {TELE_MANAS_HELPLINE} or your local emergency number. "
        "Would you like me to also connect you with a counselor?"
    )

# -----------------------
# Counselor Booking
# -----------------------
def handle_booking(parameters):
    date = parameters.get("booking_date")
    time = parameters.get("booking_time")
    method = parameters.get("contact_method")

    if date and time and method:
        return text_response(
            f"Your counselling session is booked for {date} at {time}. "
            f"You will be contacted via {method}. You are taking a strong step towards healing."
        )
    else:
        return text_response("Could you share the date, time, and whether you prefer call, chat, or video?")

# -----------------------
# Fallback (SAFE version)
# -----------------------
def handle_fallback():
    return text_response(
        f"I’m here to listen. You can start a questionnaire by saying 'Do the screening'. "
        f"If you ever feel unsafe or in crisis, please call the Tele-MANAS helpline at {TELE_MANAS_HELPLINE} "
        "or your local emergency number."
    )

# -----------------------
# Webhook route
# -----------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json(force=True)
    intent = req.get("queryResult", {}).get("intent", {}).get("displayName")
    parameters = req.get("queryResult", {}).get("parameters", {})

    if intent == "Default Welcome Intent":
        return jsonify(handle_welcome())
    elif intent == "Thanks":
        return jsonify(handle_thanks())
    elif intent == "Goodbye":
        return jsonify(handle_goodbye())
    elif intent == "Share_Problem":
        return jsonify(handle_share_problem(parameters))
    elif intent == "Offer_Screening":
        return jsonify(handle_offer_screening())
    elif intent == "PHQ-9":
        return jsonify(handle_phq9(parameters))
    elif intent == "Crisis_Suicidal":
        return jsonify(handle_crisis())
    elif intent == "Counsellor_Booking_Request":
        return jsonify(handle_booking(parameters))
    else:
        return jsonify(handle_fallback())

# -----------------------
# Run locally
# -----------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)



