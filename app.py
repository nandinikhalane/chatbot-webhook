from flask import Flask, request, jsonify

app = Flask(__name__)

# Temporary memory to store user session data (in a real app, use a database)
user_data = {}

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(force=True)
    intent = req.get("queryResult").get("intent").get("displayName")
    session_id = req.get("session", "default_session")
    
    response_text = "I'm sorry, I didn't quite get that."

    # Initialize user data for the session if it doesn't exist
    if session_id not in user_data:
        user_data[session_id] = {
            "phq9_scores": [],
            "gad7_scores": []
        }

    # --- Swasti's Intents: Welcome, Thanks, Goodbye, Default Fallback ---
    # These intents are handled directly in Dialogflow and don't require webhook logic.
    # The webhook only processes intents that need custom code (like scoring or booking).

    # --- Payal's Intents: Share_Problem, Offer_Screening ---
    # These intents are also primarily handled in Dialogflow, but we can process parameters.
    if intent == "Share_Problem":
        problem_type = req.get("queryResult").get("parameters").get("problem_type")
        if problem_type:
            # You can log or use the problem type for future personalized responses
            print(f"User is sharing a problem related to: {problem_type}")
        # The response is set directly in Dialogflow for this intent.

    # --- Disha's Intents: PHQ-9 & GAD-7 Screening Flow ---
    if intent.startswith("PHQ9_q"):
        try:
            answer = req.get("queryResult").get("parameters").get("number")
            if answer is not None:
                user_data[session_id]["phq9_scores"].append(int(answer))
            
            # Check if all 9 questions have been answered
            if len(user_data[session_id]["phq9_scores"]) == 9:
                total_score = sum(user_data[session_id]["phq9_scores"])
                
                # Determine the severity based on the total score
                if total_score <= 4:
                    result = "Minimal depression"
                elif total_score <= 9:
                    result = "Mild depression"
                elif total_score <= 14:
                    result = "Moderate depression"
                elif total_score <= 19:
                    result = "Moderately severe depression"
                else:
                    result = "Severe depression"

                response_text = f"Thanks for completing the questions. Your total PHQ-9 score is {total_score}, which suggests: {result}. You can talk to me more or book a session with a counselor."
                
                # Clear the scores for the next test
                user_data[session_id]["phq9_scores"] = []
            else:
                # Get the current question number to provide the next question response
                q_num = len(user_data[session_id]["phq9_scores"])
                phq_questions = [
                    "Q1: Over the last 2 weeks, how often have you had little interest or pleasure in doing things? (0–3)",
                    "Q2: Over the last 2 weeks, how often have you felt down, depressed, or hopeless? (0–3)",
                    "Q3: Over the last 2 weeks, how often have you had trouble falling or staying asleep, or sleeping too much? (0–3)",
                    "Q4: Over the last 2 weeks, how often have you felt tired or had little energy? (0–3)",
                    "Q5: Over the last 2 weeks, how often have you had poor appetite or overeating? (0–3)",
                    "Q6: Over the last 2 weeks, how often have you felt bad about yourself — or that you are a failure or have let yourself or your family down? (0–3)",
                    "Q7: Over the last 2 weeks, how often have you had trouble concentrating on things, such as reading or watching television? (0–3)",
                    "Q8: Over the last 2 weeks, how often have you been moving or speaking so slowly that others could notice? Or the opposite — being so fidgety or restless that you have been moving around more than usual? (0–3)",
                    "Q9: Over the last 2 weeks, how often have you had thoughts that you would be better off dead or of hurting yourself in some way? (0–3)"
                ]
                
                if q_num < len(phq_questions):
                    response_text = phq_questions[q_num]
                else:
                    response_text = "Thanks for completing the questions. I’ll analyze your answers and suggest next steps."
        except (ValueError, TypeError) as e:
            response_text = "I couldn't process your answer. Please provide a number from 0 to 3."
    
    # --- Kirti's Intents: Crisis_Suicidal, Counsellor_Booking_Request ---
    if intent == "Crisis_Suicidal":
        # This intent is for escalation handling, which is described as needing a webhook.
        # The primary response is handled in Dialogflow with the Tele-MANAS helpline info.
        # The webhook can be used here for logging the crisis or alerting a human operator.
        # For this implementation, we will simply provide a follow-up prompt.
        response_text = "I’m really concerned about your safety. If you are in immediate danger, please call the Tele-MANAS helpline (14416). Remember, I'm here to listen, and it's okay to ask for help."
        
    if intent == "Counsellor_Booking_Request":
        date = req.get("queryResult").get("parameters").get("date")
        time = req.get("queryResult").get("parameters").get("time")
        contact_method = req.get("queryResult").get("parameters").get("contact_method")
        
        # Check if all required parameters are provided by Dialogflow's slot-filling
        if date and time and contact_method:
            response_text = f"Your counselling session is booked for {date} at {time}. You will be contacted via {contact_method}."
        # If parameters are missing, Dialogflow's slot-filling prompts will handle it.
        
    return jsonify({"fulfillmentText": response_text})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
