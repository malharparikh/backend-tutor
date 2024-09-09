from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
import logging
import re
import json

from categories import categories

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def classify_prompt(prompt):
    prompt_lower = prompt.lower()

    # Check if the prompt matches any example
    for category, data in categories.items():
        for example in data.get("examples", []):
            if example.lower() == prompt_lower:
                return category

    # Check for keyword matches next
    for category, data in categories.items():
        for keyword in data["keywords"]:
            keyword_pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(keyword_pattern, prompt_lower):
                return category

    return "Other"

@app.route('/health', methods=['GET'])
def health_check():
    return "OK", 200

@app.route('/analyze', methods=['POST'])
def analyze_text():
    try:
        # Validate the incoming JSON payload
        if not request.is_json:
            return jsonify({"error": "Invalid JSON payload"}), 400
        
        data = request.json
        prompt = data.get('prompt')
        essay = data.get('essay')

        if not prompt or not essay:
            return jsonify({"error": "Missing 'prompt' or 'essay' in the request"}), 400

        logging.info(f"Received request with prompt: {prompt[:50]}...")

        # Classify the prompt
        category = classify_prompt(prompt)
        logging.info(f"Prompt classified as: {category}")

        # Ensure the category exists in the categories dictionary
        if category not in categories:
            return jsonify({"error": f"Category '{category}' not found in the categories"}), 500

        # Get category-specific overview, suggestions, and common errors
        overview = categories[category].get("overview", "")
        suggestions = categories[category].get("suggestions", "")
        common_errors = categories[category].get("common_errors", "")

        # Perform the essay analysis
        analysis = get_gpt_analysis(prompt, essay, overview, suggestions, common_errors, category)
        
        if "error" in analysis:
            return jsonify(analysis), 500

        logging.info("Analysis completed successfully")
        return jsonify(analysis)
    except Exception as e:
        logging.error(f"Error in analyze_text: {str(e)}")
        return jsonify({"error": str(e)}), 500

def get_gpt_analysis(prompt, essay, overview, suggestions, common_errors, category):
    system_message = f"""You are a College counselor and a writing assistant. Your task is to analyze the given essay based on the provided prompt.
    Provide detailed feedback on the essay's structure, content, grammar, spelling, punctuation, and relevance to the prompt. Get a thorough scan of the sentences and do not miss any errors.
    Offer specific suggestions for improvement and identify precise locations of errors with clear corrections.

    Overview: {overview}
    Suggestions: {suggestions}
    Common Errors: {common_errors}
    """

    user_message = f"""Prompt: {prompt}

Essay:
{essay}

Analyze the essay and provide a response in the following format:

CONTENT_FEEDBACK:
[Provide overall feedback on the essay's content, structure, and relevance to the prompt. Include at least one sentence identifying the most pressing issues that could be improved.]

SPELLING_ERRORS:
[List each spelling error, its correction, and its position in the essay. If no errors, write "None found."]

GRAMMAR_ERRORS:
[List each grammar error, its suggested correction, and its position in the essay. If no errors, write "None found."]

PUNCTUATION_ERRORS:
[List each punctuation error, its suggested correction, and its position in the essay. If no errors, write "None found."]

IMPROVEMENT_SUGGESTIONS:
[List specific suggestions for improving the essay. For each suggestion, include an additional sentence explaining why the change is necessary and how to implement it.]

Make sure to identify and specify all types of errors accurately. Ensure the feedback is written in the second person ('you') instead of referring to 'the applicant'. Highlight specific sentences that could be rewritten for clarity and address any big picture issues."""

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json().get('choices', [])[0].get('message', {}).get('content', '')
      

        sections = [
        "CONTENT_FEEDBACK",
        "SPELLING_ERRORS",
        "GRAMMAR_ERRORS",
        "PUNCTUATION_ERRORS",
        "IMPROVEMENT_SUGGESTIONS"
    ]
    
        # Initialize variables
        content_feedback = ""
        spelling_errors = ""
        grammar_errors = ""
        punctuation_errors = ""
        improvement_suggestions = ""
        
        # Split the text into lines
        lines = result.split('\n')
        
        current_section = ""
        for line in lines:
            # Check if the line is a section header
            if any(section in line for section in sections):
                current_section = line.strip(':')
            elif current_section:
                # Add content to the appropriate variable
                if current_section == "CONTENT_FEEDBACK":
                    content_feedback += line + "\n"
                elif current_section == "SPELLING_ERRORS":
                    spelling_errors += line + "\n"
                elif current_section == "GRAMMAR_ERRORS":
                    grammar_errors += line + "\n"
                elif current_section == "PUNCTUATION_ERRORS":
                    punctuation_errors += line + "\n"
                elif current_section == "IMPROVEMENT_SUGGESTIONS":
                    improvement_suggestions += line + "\n"
            # Process errors and suggestions
            print(content_feedback, "RESULRT")

        return {
            "category": category,
            "content_feedback": content_feedback.strip(),
            "spelling_errors": spelling_errors.strip(),
            "grammar_errors": grammar_errors.strip(),
            "punctuation_errors": punctuation_errors.strip(),
            "improvement_suggestions": improvement_suggestions.strip(),
            "word_count": len(essay.split()),
            "prompt": prompt
        }

    except requests.exceptions.RequestException as e:
        logging.error(f"Error in get_gpt_analysis: {str(e)}")
        return {
            "error": f"Failed to get analysis from GPT: {str(e)}",
            "status_code": getattr(e.response, 'status_code', None)
        }
    except Exception as e:
        logging.error(f"Unexpected error in get_gpt_analysis: {str(e)}")
        return {
            "error": f"An unexpected error occurred: {str(e)}",
            "raw_response": result if 'result' in locals() else "No response received"
        }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
