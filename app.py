from flask import Flask, request, jsonify

app = Flask(__name__)

# Temporary storage for user sessions (for demo only)
user_sessions = {}

# PHQ-9 Questions
PHQ9_QUESTIONS = [
    "Over the last 2 weeks, how often have you had little interest or pleasure in doing things?",
    "Over the last 2 weeks, how often have you felt down, depressed, or hopeless?",
    "Over the last 2 weeks, how often have you had trouble falling or staying asleep, or sleeping too much?",
    "Over the last 2 weeks, how often have you felt tired or had little energy?",
    "Over the last 2 weeks, how often have you had poor appetite or overeating?",
    "Over the last 2 weeks, how often have you felt bad about yourself or that you are a failure?",
    "Over the last 2 weeks, how often have you had trouble concentrating on things?",
    "Over the last 2 weeks, how often have you moved or spoken so slowly that other people noticed?",
    "Over the last 2 weeks, how often have you had thoughts that you would be better off dead or hurting yourself?"
]

# GAD-7 Questions
GAD7_QUESTIONS = [
    "Over the last 2 weeks, how often have you felt nervous, anxious, or on edge?",
    "Over the last 2 weeks, how often have you not been able to stop or control worrying?",
    "Over the last 2 weeks, how often have you worried too much about different things?",
    "Over the last 2 weeks, how often have you had trouble relaxing?",
    "Over the last 2 weeks, how often have you been so restless that it’s hard to sit still?",
    "Over the last 2 weeks, how often have you become easily annoyed or irritable?",
    "Over the last 2 weeks, how often have you felt afraid as if something awful might happen?"
]

@app.route('/')
def home():
    return "✅ Webhook with PHQ-9 & GAD-7 scoring is live!"

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    intent = req.get("queryResult", {}).get("intent", {}).get("displayName", "")
    session_id = req.get("session", "default_session")

    # Create session if new
    if session_id not in user_sessions:
        user_sessions[session_id] = {"phq9": [], "gad7": [], "mode": None}

    session_data = user_sessions[session_id]
    response_text = "I'm here with you."

    # ---- Start PHQ-9 ----
    if intent == "PHQ9_Start":
        session_data["mode"] = "phq9"
        session_data["phq9"] = []  # reset answers
        response_text = PHQ9_QUESTIONS[0]

    elif session_data["mode"] == "phq9":
        # Capture answer as a score (assume user replies 0-3)
        user_input = req.get("queryResult", {}).get("queryText", "").strip()
        try:
            score = int(user_input)
            if score in [0,1,2,3]:
                session_data["phq9"].append(score)
        except:
            pass

        # Next question or finish
        if len(session_data["phq9"]) < len(PHQ9_QUESTIONS):
            response_text = PHQ9_QUESTIONS[len(session_data["phq9"])]
        else:
            total = sum(session_data["phq9"])
            if total <= 4:
                severity = "Minimal depression"
            elif total <= 9:
                severity = "Mild depression"
            elif total <= 14:
                severity = "Moderate depression"
            elif total <= 19:
                severity = "Moderately severe depression"
            else:
                severity = "Severe depression"

            response_text = f"Your PHQ-9 score is {total}/27 → {severity}. Would you like to talk to a counselor?"

            session_data["mode"] = None  # reset

    # ---- Start GAD-7 ----
    elif intent == "GAD7_Start":
        session_data["mode"] = "gad7"
        session_data["gad7"] = []
        response_text = GAD7_QUESTIONS[0]

    elif session_data["mode"] == "gad7":
        user_input = req.get("queryResult", {}).get("queryText", "").strip()
        try:
            score = int(user_input)
            if score in [0,1,2,3]:
                session_data["gad7"].append(score)
        except:
            pass

        if len(session_data["gad7"]) < len(GAD7_QUESTIONS):
            response_text = GAD7_QUESTIONS[len(session_data["gad7"])]
        else:
            total = sum(session_data["gad7"])
            if total <= 4:
                severity = "Minimal anxiety"
            elif total <= 9:
                severity = "Mild anxiety"
            elif total <= 14:
                severity = "Moderate anxiety"
            else:
                severity = "Severe anxiety"

            response_text = f"Your GAD-7 score is {total}/21 → {severity}. Do you want me to suggest coping strategies or connect you with a counselor?"

            session_data["mode"] = None

    return jsonify({"fulfillmentText": response_text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

