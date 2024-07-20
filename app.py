from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
import logging

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@app.route('/health', methods=['GET'])
def health_check():
    return "OK", 200

@app.route('/analyze', methods=['POST'])
def analyze_text():
    try:
        prompt = request.json['prompt']
        essay = request.json['essay']
        logging.info(f"Received request with prompt: {prompt[:50]}...")
        analysis = get_gpt_analysis(prompt, essay)
        logging.info("Analysis completed successfully")
        return jsonify(analysis)
    except Exception as e:
        logging.error(f"Error in analyze_text: {str(e)}")
        return jsonify({"error": str(e)}), 500

def get_gpt_analysis(prompt, essay):
    system_message = """You are a College counselor and a writing assistant. Your task is to analyze the given essay based on the provided prompt.
    Provide detailed feedback on the essay's structure, content, grammar, spelling, punctuation, and relevance to the prompt.
    Offer specific suggestions for improvement and identify precise locations of errors with clear corrections. Your response should be in a structured format for easy parsing."""

    user_message = f"""Prompt: {prompt}
Essay:
{essay}
Analyze the essay and provide a response in the following JSON format:
{{
    "spelling_errors": [
        {{"error": "misspelled word", "correction": "correct spelling", "position": "word index in essay"}}
    ],
    "grammar_errors": [
        {{"error": "grammar error description", "suggestion": "corrected version", "position": "start index of error"}}
    ],
    "punctuation_errors": [
        {{"error": "punctuation error description", "suggestion": "corrected version", "position": "index of error"}}
    ],
    "content_feedback": "Provide overall feedback on the essay's content, structure, and relevance to the prompt",
    "improvement_suggestions": [
        "List specific suggestions for improving the essay"
    ]
}}
Make sure to identify and specify all types of errors accurately, including spelling, grammar, and punctuation. If there are no errors in a category, provide an empty array for that category. Ensure the response is a valid JSON object."""

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()['choices'][0]['message']['content']
        return {
            "analysis": result,
            "word_count": len(essay.split()),
            "prompt": prompt
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"Error in get_gpt_analysis: {str(e)}")
        return {
            "error": f"Failed to get analysis from GPT: {str(e)}",
            "status_code": response.status_code if hasattr(response, 'status_code') else None
        }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
