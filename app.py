from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
import logging
import re
import json
from prompt_classifier import classify_prompt
from categories import categories

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
        # overview = categories[category].get("overview", "")
        # suggestions = categories[category].get("suggestions", "")
        # common_errors = categories[category].get("common_errors", "")

        # Perform the essay analysis
        analysis = get_gpt_analysis(prompt, essay, category)
        
        if "error" in analysis:
            return jsonify(analysis), 500

        logging.info("Analysis completed successfully")
        return jsonify(analysis)
    except Exception as e:
        logging.error(f"Error in analyze_text: {str(e)}")
        return jsonify({"error": str(e)}), 500

def get_gpt_analysis(prompt, essay, category):
    # Fetch additional information based on the category
    category_info = categories.get(category, {})
    category_overview = category_info.get("overview", "No overview available.")
    category_suggestions = category_info.get("suggestions", "No specific suggestions available.")
    category_common_errors = category_info.get("common_errors", [])

    # Define the system and user messages for GPT, including category-specific information
    system_message = f"""You are a college admissions counselor with a strict approach to grammar and content. Your task is to rigorously analyze this college admissions essay and provide extremely detailed feedback.
    
    For this specific essay category:
    - {category_overview}
    
    Be especially mindful of the following suggestions when providing improvement feedback:
    - {category_suggestions}
    
    The essay must be flawless in terms of grammar, spelling, punctuation, and clarity. Identify every error, no matter how small, and be particularly strict about:
    - Sentence structure
    - Tense consistency
    - Subject-verb agreement
    - Article usage (a, an, the)
    - Punctuation placement
    - Transitions and conjunctions
    - Repetitive sentence patterns or awkward phrasing

    When analyzing the essay's content, provide constructive criticism to ensure it answers the prompt effectively and improves the applicant's chances of admission.

    Format for feedback:
    - CONTENT_FEEDBACK: 1 line overview, 1 line explanation, 1 line specific location in the essay
    - SPELLING_ERRORS: Quote the error directly from the essay, provide correction, and indicate its exact position.
    - GRAMMAR_ERRORS: Quote the error, suggest a correction, and provide its exact position.
    - PUNCTUATION_ERRORS: Quote the punctuation error, suggest correction, and provide its exact position.
    - IMPROVEMENT_SUGGESTIONS: Provide strict improvement suggestions that align with college admissions requirements. Avoid suggesting 'proofreading' and be specific about how the change would positively impact the essay's readability or relevance."""

    user_message = f"""Prompt: {prompt}

Essay:
{essay}

Analyze the essay and provide a response in the following format:

CONTENT_FEEDBACK:
[1 line overview, 1 line explanation, 1 line location in the essay]

SPELLING_ERRORS:
[Quote the error, provide correction, and indicate position]

GRAMMAR_ERRORS:
[Quote the error, provide correction, and indicate position]

PUNCTUATION_ERRORS:
[Quote the error, provide correction, and indicate position]

IMPROVEMENT_SUGGESTIONS:
[Strict improvement suggestions related to clarity and effectiveness of the essay. Conclude with how these changes would affect the overall quality of the essay.]"""

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.1,  # Low temperature for consistent responses
        "max_tokens": 2000    # Increased token limit for detailed output
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=30)
        response.raise_for_status()  # Check if request is successful
        result = response.json().get('choices', [])[0].get('message', {}).get('content', '')
        
        # Log the result for debugging purposes
        logging.debug(f"GPT-4 response: {result}")

        if not result:
            raise ValueError("Empty result received from the GPT API")

        # Initialize variables for each section
        sections = {
            "CONTENT_FEEDBACK": "",
            "SPELLING_ERRORS": "",
            "GRAMMAR_ERRORS": "",
            "PUNCTUATION_ERRORS": "",
            "IMPROVEMENT_SUGGESTIONS": ""
        }

        # Track the current section
        current_section = None
        
        # Process each line in the result
        for line in result.splitlines():
            line = line.strip()  # Remove leading/trailing spaces

            # Check if the line starts with a section header
            for section in sections.keys():
                if line.startswith(section + ":"):
                    current_section = section
                    line = line[len(section) + 1:].strip()  # Remove section header and colon
                    break

            # If inside a section, append the content
            if current_section:
                sections[current_section] += line + "\n"

        # Handle common errors for spelling, grammar, and punctuation
        if not sections["SPELLING_ERRORS"].strip() and category_common_errors:
            sections["SPELLING_ERRORS"] = "Common spelling errors:\n" + "\n".join(category_common_errors.get("spelling", []))

        if not sections["GRAMMAR_ERRORS"].strip() and category_common_errors:
            sections["GRAMMAR_ERRORS"] = "Common grammar errors:\n" + "\n".join(category_common_errors.get("grammar", []))

        if not sections["PUNCTUATION_ERRORS"].strip() and category_common_errors:
            sections["PUNCTUATION_ERRORS"] = "Common punctuation errors:\n" + "\n".join(category_common_errors.get("punctuation", []))

        # Post-process sections to handle empty content
        for section, content in sections.items():
            if not content.strip():
                sections[section] = "No errors found" if "ERRORS" in section else "No suggestions found"

        # Return the response in a structured format
        return {
            "category": category,
            "content_feedback": sections["CONTENT_FEEDBACK"].strip(),
            "spelling_errors": sections["SPELLING_ERRORS"].strip(),
            "grammar_errors": sections["GRAMMAR_ERRORS"].strip(),
            "punctuation_errors": sections["PUNCTUATION_ERRORS"].strip(),
            "improvement_suggestions": sections["IMPROVEMENT_SUGGESTIONS"].strip(),
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
