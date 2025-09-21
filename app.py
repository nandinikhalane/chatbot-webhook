"""
Dialogflow Webhook in Python (Flask)
Handles:
- PHQ-9 / GAD-7 scoring
- Crisis escalation
- Counsellor booking
"""

from flask import Flask, request, jsonify
import os

app = Flask(__name__)

TELE_MANAS_HELPLINE = os.environ.get("HELPLINE_NUMBER", "14416")

# ------------------ Helpers ------------------

def extract_numeric_answers(query_result, prefix, num_questions):
    """Try to read answers from parameters or contexts"""
    params = query_result.get("parameters", {})
    answers = []

    # 1) Parameters like phq9_q1...phq9_q9
    for i in range(1, num_questions + 1):
        key = f"{prefix}_q{i}"
        if key in params:
            try:
                answers.append(int(params[key]))
            except Exception:
                pass
    if len(answers) == num_questions:
        return answers

    # 2) Parameters as array: phq9_answers
    arr_key = f"{prefix}_answers"
    if isinstance(params.get(arr_key), list) and len(params[arr_key]) >= num_questions:
        try:
            return [int(x) for x in params[arr_key][:num_questions]]
        except Exception:
            pass

    # 3) Check contexts
    for ctx in query_result.get("outputContexts", []):
        ctx_params = ctx.get("parameters", {})
        answers = []
        found = True
        for i in range(1, num_questions + 1):
            key = f"{prefix}_q{i}"
            if key in ctx_params:
                try:
                    answers.append(int(ctx_params[key]))
                except Exception:
                    found = False
                    break
            else:
                found = False
                break
        if found and len(answers) == num_questions:
            return answers

        if isinstance(ctx_params.get(arr_key), list) and len(ctx_params[arr_key]) >= num_questions:
            try:
                return [int(x) for x in ctx_params[arr_key][:num_questions]]
            except Exception:
                pass

    return None


def score_phq9(answers):
    total = sum(answers)
    if total <= 4:
        severity = "Minimal or none"
    elif total <= 9:
        severity = "Mild"
    elif total <= 14:
        severity = "Moderate"
    elif total <= 19:
        severity = "Moderately severe"
    else:
        severity = "Severe"
    suicidal_item = answers[8] > 0  # Q9
    return total, severity, suicidal_item


def score_gad7(answers):
    total = sum(answers)
    if total <= 4:
        severity = "Minimal or none"
    elif total <= 9:
        severity = "Mild"
    elif total <= 14:
        severity = "Moderate"
    else:
        severity = "Severe"
    return total, severity


def text_response(text, output_contexts=None):
    resp = {
        "fulfillmentText": text,
        "fulfillmentMessages": [{"text": {"text": [text]}}],
    }
    if output_contexts:
        resp["outputContexts"] = output_contexts
    return resp

# ------------------ Routes ------------------

@app.route("/", methods=["GET"])
def health():
    return "Dialogflow webhook running", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_json(force=True)
    query_result = body.get("queryResult", {})
    intent_name = query_result.get("intent", {}).get("displayName", "")
    print("Incoming intent:", intent_name)

    # Crisis handling
    if intent_name.lower().startswith("crisis") or "suicid" in intent_name.lower():
        text = (f"I’m really concerned about your safety. If you are in immediate danger, "
                f"please call the Tele-MANAS helpline ({TELE_MANAS_HELPLINE}) or your local emergency number. "
                f"Would you like me to connect you to a counselor?")
        output_contexts = [{
            "name": f"{query_result['outputContexts'][0]['name'].split('/contexts/')[0]}/contexts/escalation_flag"
            if query_result.get("outputContexts") else "escalation_flag",
            "lifespanCount": 5,
            "parameters": {"escalation_required": True, "reason": "suicidal_ideation"}
        }]
        return jsonify(text_response(text, output_contexts))

    # PHQ-9 completion
    if "phq9" in intent_name.lower():
        answers = extract_numeric_answers(query_result, "phq9", 9)
        if not answers:
            return jsonify(text_response("I didn’t get all the PHQ-9 answers. Please answer each question with 0–3."))

        total, severity, suicidal = score_phq9(answers)

        if suicidal or total >= 20:
            text = (f"Your PHQ-9 score is {total} ({severity}). Because of high distress or self-harm thoughts, "
                    f"I recommend immediate support. Would you like me to connect you to the Tele-MANAS helpline "
                    f"({TELE_MANAS_HELPLINE}) or a counselor?")
            ctxs = [{
                "name": f"{query_result['outputContexts'][0]['name'].split('/contexts/')[0]}/contexts/phq9_result"
                if query_result.get("outputContexts") else "phq9_result",
                "lifespanCount": 10,
                "parameters": {"phq9_score": total, "phq9_severity": severity, "suicidalItem": suicidal}
            }, {
                "name": f"{query_result['outputContexts'][0]['name'].split('/contexts/')[0]}/contexts/escalation_flag"
                if query_result.get("outputContexts") else "escalation_flag",
                "lifespanCount": 5,
                "parameters": {"escalation_required": True, "reason": "phq9_severe_or_suicidal"}
            }]
            return jsonify(text_response(text, ctxs))

        # Non-critical response
        if total <= 4:
            suggestion = "Minimal symptoms. Self-care may help (sleep, exercise, social support)."
        elif total <= 9:
            suggestion = "Mild symptoms. Consider self-help strategies and monitor your mood."
        elif total <= 14:
            suggestion = "Moderate symptoms. Talking to a counselor could help."
        else:
            suggestion = "Moderately severe symptoms. Professional support is strongly recommended."

        text = f"Your PHQ-9 score is {total} ({severity}). {suggestion}"
        ctxs = [{
            "name": f"{query_result['outputContexts'][0]['name'].split('/contexts/')[0]}/contexts/phq9_result"
            if query_result.get("outputContexts") else "phq9_result",
            "lifespanCount": 10,
            "parameters": {"phq9_score": total, "phq9_severity": severity}
        }]
        return jsonify(text_response(text, ctxs))

    # GAD-7 completion
    if "gad7" in intent_name.lower():
        answers = extract_numeric_answers(query_result, "gad7", 7)
        if not answers:
            return jsonify(text_response("I didn’t get all the GAD-7 answers. Please answer each question with 0–3."))
        total, severity = score_gad7(answers)
        advice = "Talking to a counselor may help." if total >= 10 else "You may try some self-care strategies."
        text = f"Your GAD-7 score is {total} ({severity}). {advice}"
        ctxs = [{
            "name": f"{query_result['outputContexts'][0]['name'].split('/contexts/')[0]}/contexts/gad7_result"
            if query_result.get("outputContexts") else "gad7_result",
            "lifespanCount": 10,
            "parameters": {"gad7_score": total, "gad7_severity": severity}
        }]
        return jsonify(text_response(text, ctxs))

    # Booking intent
    if "booking" in intent_name.lower():
        params = query_result.get("parameters", {})
        date = params.get("booking_date")
        time = params.get("booking_time")
        method = params.get("contact_method")

        if not (date and time and method):
            return jsonify(text_response("To book, I need a date, time, and contact method. Can you provide those?"))

        # Here you can call an external booking API if available
        text = f"Your counselling session is booked for {date} at {time}. You will be contacted via {method}."
        ctxs = [{
            "name": f"{query_result['outputContexts'][0]['name'].split('/contexts/')[0]}/contexts/booking_confirmed"
            if query_result.get("outputContexts") else "booking_confirmed",
            "lifespanCount": 5,
            "parameters": {"booking_date": date, "booking_time": time, "contact_method": method}
        }]
        return jsonify(text_response(text, ctxs))

    # Default fallback
    fallback = ("Thanks — I got your message. If you want to take a short questionnaire (PHQ-9 or GAD-7), "
                "say 'Do the screening'. If you're in crisis, type 'I want to die'.")
    return jsonify(text_response(fallback))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


