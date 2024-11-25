import os
import requests
import logging
from categories import categories
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_gpt_analysis(prompt, essay, category):
    category_info = categories.get(category, {})
    category_overview = category_info.get("overview", "No overview available.")
    category_suggestions = category_info.get("suggestions", "No specific suggestions available.")
    category_common_errors = category_info.get("common_errors", [])

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
    - CONTENT_FEEDBACK: 1st point: Overall feedback of the essay (be harsh and critique), 2nd point: Feedback related to prompt relevance, 3rd point: Most concerning line from the essay that you get in the input, in quotes.
    - SPELLING_ERRORS: Quote the error directly from the essay, provide correction, and indicate its exact position.
    - GRAMMAR_ERRORS: Quote the error, suggest a correction, and provide its exact position.
    - PUNCTUATION_ERRORS: Quote the punctuation error, suggest correction, and provide its exact position.
    - IMPROVEMENT_SUGGESTIONS: Provide strict improvement suggestions that align with college admissions requirements. Avoid suggesting 'proofreading' and be specific about how the change would positively impact the essay's readability or relevance."""

    user_message = f"""Prompt: {prompt}

Essay:
{essay}

Analyze the essay and provide a response in the following format:

CONTENT_FEEDBACK:
[1st point: Overall feedback (be harsh), 2nd point: Feedback related to prompt relevance, 3rd point: Most concerning line, in quotes.]

SPELLING_ERRORS:
[Quote the error, provide correction, and indicate position and if no errors then just return 'No errors found']

GRAMMAR_ERRORS:
[Quote the error, provide correction, and indicate position and if no errors then just return 'No errors found']

PUNCTUATION_ERRORS:
[Quote the punctuation error, provide correction, and indicate position and if no errors then just return 'No errors found']

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
        "temperature": 0.1,
        "max_tokens": 2000
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json().get('choices', [])[0].get('message', {}).get('content', '')

        if not result:
            raise ValueError("Empty result received from the GPT API")

        logging.debug(f"GPT-4 response: {result}")

        sections = {
            "CONTENT_FEEDBACK": "",
            "SPELLING_ERRORS": "",
            "GRAMMAR_ERRORS": "",
            "PUNCTUATION_ERRORS": "",
            "IMPROVEMENT_SUGGESTIONS": ""
        }
        
        current_section = None
        
        for line in result.splitlines():
            line = line.strip()
            for section in sections.keys():
                if line.startswith(section + ":"):
                    current_section = section
                    line = line[len(section) + 1:].strip()
                    break

            if current_section:
                sections[current_section] += line + "\n"
        
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
