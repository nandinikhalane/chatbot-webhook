import json
import os
from flask import Flask, request, jsonify
from google.cloud import dialogflow_v2 as dialogflow
from google.cloud import language_v1

# Initialize Flask app
app = Flask(__name__)

# Set up Google Cloud client for sentiment analysis
sentiment_client = language_v1.LanguageServiceClient()

# Initialize PHQ-9 and GAD-7 questions and their corresponding entities
PHQ9_QUESTIONS = [
    "Q1: Over the last 2 weeks, how often have you had little interest or pleasure in doing things?",
    "Q2: Over the last 2 weeks, how often have you felt down, depressed, or hopeless?",
    "Q3: Over the last 2 weeks, how often have you had trouble falling or staying asleep, or sleeping too much?",
    "Q4: Over the last 2 weeks, how often have you felt tired or had little energy?",
    "Q5: Over the last 2 weeks, how often have you had poor appetite or overeating?",
    "Q6: Over the last 2 weeks, how often have you felt bad about yourself — or that you are a failure or have let yourself or your family down?",
    "Q7: Over the last 2 weeks, how often have you had trouble concentrating on things, such as reading or watching television?",
    "Q8: Over the last 2 weeks, how often have you been moving or speaking so slowly that others could notice? Or the opposite — being so fidgety or restless that you have been moving around more than usual?",
    "Q9: Over the last 2 weeks, how often have you had thoughts that you would be better off dead or of hurting yourself in some way?"
]

GAD7_QUESTIONS = [
    "Q1: Over the last 2 weeks, how often have you felt nervous, anxious, or on edge?",
    "Q2: Over the last 2 weeks, how often have you not been able to stop or control worrying?",
    "Q3: Over the last 2 weeks, how often have you been worrying too much about different things?",
    "Q4: Over the last 2 weeks, how often have you had trouble relaxing?",
    "Q5: Over the last 2 weeks, how often have you been so restless that it is hard to sit still?",
    "Q6: Over the last 2 weeks, how often have you been easily annoyed or irritable?",
    "Q7: Over the last 2 weeks, how often have you felt afraid as if something awful might happen?"
]

# Scoring thresholds
PHQ9_THRESHOLDS = {
    'mild': 5,
    'moderate': 10,
    'severe': 20
}

GAD7_THRESHOLDS = {
    'mild': 5,
    'moderate': 10,
    'severe': 15
}

def analyze_sentiment(text):
    """Detects sentiment in the provided text."""
    document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)
    sentiment = sentiment_client.analyze_sentiment(request={'document': document}).document_sentiment
    return sentiment.score, sentiment.magnitude

def get_context_parameter(context_list, context_name, param_name):
    """
    Extracts a parameter value from a specific context in the webhook request.
    """
    for context in context_list:
        if context.get('name').endswith(f'/contexts/{context_name}'):
            return context.get('parameters', {}).get(param_name)
    return None

@app.route('/webhook', methods=['POST'])
def webhook():
    """DialogFlow webhook handler."""
    req = request.get_json(silent=True, force=True)
    intent_name = req['queryResult']['intent']['displayName']
    
    # 🚨 Safety Layer: Check sentiment for every message
    user_text = req['queryResult']['queryText']
    sentiment_score, _ = analyze_sentiment(user_text)

    # Immediate crisis detection
    if sentiment_score <= -0.8 or intent_name == 'Crisis_Suicidal':
        return handle_crisis_escalation(req)

    if intent_name == 'PHQ9_q9':
        return handle_phq9_completion(req)
    
    # Check for GAD-7 completion
    elif intent_name == 'GAD7_q7':
        return handle_gad7_completion(req)

    elif intent_name == 'Counsellor_Booking_Request':
        return handle_counsellor_booking(req)

    # Handle all other intents without webhook logic by default
    return jsonify({
        'fulfillmentText': req['queryResult']['fulfillmentText']
    })

def handle_phq9_completion(req):
    """
    Calculates the PHQ-9 score and provides a response based on severity.
    """
    phq9_score = 0
    # Retrieve score parameters from the 'in_phq9' context
    contexts = req.get('queryResult', {}).get('outputContexts', [])
    for i in range(1, 10):
        try:
            param_name = f'phq9_q{i}.original'
            score_str = get_context_parameter(contexts, 'in_phq9', param_name)
            if score_str is not None:
                phq9_score += int(score_str)
        except (ValueError, TypeError):
            continue

    response_text = "Thanks for completing the questions. Based on your answers, "
    
    if phq9_score < PHQ9_THRESHOLDS['mild']:
        response_text += "your score suggests a minimal level of depression. Focusing on self-care and staying connected with friends can be helpful."
    elif phq9_score < PHQ9_THRESHOLDS['moderate']:
        response_text += "your score suggests mild to moderate depression. Talking to a professional counselor could be a great next step. Would you like to book a session?"
    else: # Severe
        response_text += "your score suggests a severe level of depression. It's really important to get help right away. Talking to a professional could make a huge difference. Would you like me to connect you to the Tele-MANAS helpline?"

    return jsonify({
        'fulfillmentText': response_text
    })

def handle_gad7_completion(req):
    """
    Calculates the GAD-7 score and provides a response based on severity.
    """
    # This logic would be similar to the PHQ-9 handler, using GAD7_THRESHOLDS.
    # We would need to retrieve parameters from an 'in_gad7' context.
    # For brevity, this is left as a placeholder, as the provided flow focuses on PHQ-9.
    return jsonify({
        'fulfillmentText': "Thanks for completing the GAD-7 questions. I'll analyze your answers and suggest next steps."
    })

def handle_crisis_escalation(req):
    """
    Provides an immediate and direct crisis response.
    """
    # This intent is a red flag. Give direct, actionable advice.
    crisis_response = "I'm really concerned about your safety. If you are in immediate danger, please call the Tele-MANAS helpline at 14416. We can talk more, but your safety is the most important thing right now. Would you like to connect to a helpline or a counselor?"
    
    # The webhook can also trigger an email or SMS alert to a human team
    # log_crisis_alert(req['session'], req['queryResult']['queryText'])
    
    return jsonify({
        'fulfillmentText': crisis_response
    })

def handle_counsellor_booking(req):
    """
    Confirms the booking with the user and could be extended to
    connect to an external calendar API.
    """
    parameters = req['queryResult']['parameters']
    date = parameters.get('booking_date')
    time = parameters.get('booking_time')
    method = parameters.get('contact_method')

    if not all([date, time, method]):
        # This part is handled by DialogFlow's slot-filling.
        # This webhook function will only be called after all slots are filled.
        return jsonify({
            'fulfillmentText': "I need a few more details to book your session."
        })

    confirmation_text = f"Your counselling session is booked for {date} at {time}. You will be contacted via {method}."
    
    # Here you would integrate with a booking API (e.g., Google Calendar, a custom backend)
    # try:
    #   book_session_in_backend(date, time, method)
    #   confirmation_text = "Your session is confirmed!"
    # except Exception as e:
    #   confirmation_text = "I'm sorry, I couldn't book your session right now. Please try again later."
    
    return jsonify({
        'fulfillmentText': confirmation_text
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)



