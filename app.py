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

# Define your categories with example prompts and related data
categories = {
    "Why this school": {
        "keywords": ["why", "community", "join", "apply", "contribute", "fit", "match"],
        "examples": [
            "Describe why you are interested in joining the Tulane community. Consider your experiences, talents, and values to illustrate what you would contribute to the Tulane community if admitted. This statement should be 250 words at most; however, it is neither necessary nor expected that you reach this maximum length. We strongly encourage you to focus on content and efficiency rather than word count. While submitting this prompt is optional, we recommend that all applicants do so.",
            "We want to be sure we’re considering your application in the context of your personal experiences: What aspects of your background, your identity, or your school, community, and/or household settings have most shaped how you see yourself engaging in Northwestern’s community, be it academically, extracurricularly, culturally, politically, socially, or otherwise?",
            "What is it about Yale that has led you to apply?",
            "What is your sense of Duke as a university and a community, and why do you consider it a good match for you? If there‘s something in particular about our offerings that attracts you, feel free to share that as well."
        ],
        "overview": "The 'Why This College' essay is the most common type of supplemental essay, offering a chance to demonstrate your genuine interest and fit with a particular school. Essay readers are looking for well-researched, specific reasons why you want to attend their institution, not just vague statements about the school's size, location, or reputation. The best essays will incorporate detailed examples of the school's unique programs, faculty, or philosophy that align with your own interests and goals. It's crucial to emphasize how these aspects resonate with your personality and aspirations, showcasing your enthusiasm and the mutual fit between you and the institution. Avoid common pitfalls like overusing emotional language without concrete reasoning, relying on cliches or generalizations, or referencing well-known traditions that don’t add value to your narrative. Instead, focus on specific details that highlight your commitment and excitement, making your essay a compelling argument for why you and the school are a perfect match.",
        "suggestions": [
            "Treat each “why us” essay individually",
            "Make sure the essay is not too general",
            "Use details and examples specific to the school",
            "Do your research",
            "Your examples and reasoning should use specific details about the school such as specific course offerings, extracurricular programs, or elements of the school's philosophy to demonstrate your interest.",
            "More specific details are better than less specific. For example, your interest in the size of the school would be less compelling than your interest in a specific peer-mentoring program in your department.",
            "It’s not enough to simply mention a strong department. Include specific examples about programs, research opportunities or individuals within the department which you can find on the department website.",
            "If you went on a tour of the school, mention that as it will help demonstrate your committed interest. You can cite specific information you learned about the school from your visit.",
            "Focus on your “fit”",
            "You should discuss not only the things that appeal to you about the school but also about why you are a good fit for these opportunities.",
            "Focus on the institution's strengths and how these align with your own interests and your personality as a whole.",
            "Be enthusiastic",
            "Communicate your excitement as this will help communicate to essay readers that you will be likely to accept if you apply (this helps their matriculation rates).",
            "Talk about a positive interaction you had with a member of the community or a specific experience from your visit that demonstrates your excitement.",
            "Essay readers are just people who loved the school so much they decided to stay and start their careers. Try to appeal to their enthusiasm and love for the school.",
            "Avoid generalizations or cliches that may come across as insincere."
        ],
        "common_errors": [
            "Writing about the school's size, location, reputation, weather, or ranking. Many other students are also writing about these topics and they don’t demonstrate that you’ve done the research.",
            "Being overly reliant on emotional language: 'It just felt right' and 'I could see myself rooting for the Trojans on Saturdays' are very general and don’t show the reader why you are a good match for the school.",
            "You can use emotional language, but make sure to back it up with specific reasoning.",
            "Getting school colors, mascots, or slogans wrong: Referencing these branding aspects at the school can sometimes be cliche. If you’re going to do it, make sure you’re getting the information correct.",
            "Describing traditions that the school is well known for: Avoid referencing traditions or rights of passage that are well known, as many other students will be referencing these too. You can’t use these to demonstrate why you’re a good fit. If you can search ‘school name + traditions’ in google and it comes up then you shouldn’t use it.",
            "Thinking of the essay as a 'why this school': Try thinking of this essay as a 'why us together' instead of a 'why this school'."
        ]
    },
    "Academic Interests": {
        "keywords": ["academic", "study", "major", "interests", "learning", "goals", "education"],
        "examples": [
            "Why are you drawn to studying the major you have selected? Please discuss how your interests and related experiences have influenced your choice. How will an education from the College of Agriculture and Life Sciences (CALS) at Cornell University specifically serve to support your learning, growth, and the pursuit of your goals?",
            "What do you hope to study, and why, at CU Boulder? Or if you don‘t know quite yet, think about your studies so far, extracurricular/after-school activities, jobs, volunteering, future goals, or anything else that has shaped your interests.",
            "Students at Yale have plenty of time to explore their academic interests before committing to one or more major fields of study. Many students either modify their original academic direction or change their minds entirely. As of this moment, what academic areas seem to fit your interests or goals most comfortably? Please indicate up to three from the list provided.",
            "Tell us about a topic or idea that excites you and is related to one or more academic areas you selected above. Why are you drawn to it?",
            "Describe how you plan to pursue your academic interests and why you want to explore them at USC specifically. Please feel free to address your first- and second-choice major selections."
        ],
        "overview": "This essay focuses on your academic passions and how the school aligns with them. Essay readers are interested in understanding why you are passionate about your chosen field of study and how the school's offerings can help you achieve your academic and professional goals. The most compelling essays will demonstrate deep knowledge and enthusiasm for your chosen field, and explain how specific programs, faculty, or opportunities at the school will support your academic journey. Avoid being too broad or too technical; instead, focus on specific aspects of the academic program that resonate with you and how they align with your future aspirations.",
        "suggestions": [
            "Be enthusiastic: Demonstrate your passion for your chosen area by being authentically enthusiastic.",
            "Some tips to demonstrate your enthusiasm include being specific in your interest (showing not telling), doing research and relating it to specific offerings by the school.",
            "Choosing something you are genuinely passionate about will make it easier and you should find that you have too many words not too few.",
            "Be specific: Being as specific about your academic interests/passions as possible will let you demonstrate your deep knowledge in this niche as well as help make your enthusiasm feel realistic.",
            "Typically it is most effective to write about your indicated major.",
            "If you don’t you will have to explain how the interest you choose fits in with your major/study plans.",
            "Discuss why the topic is important to you and for the world: The essay reader wants to know what it would mean for you to be able to study at their school. Describe why this opportunity would be valuable to you, to those around you, and what you hope to contribute to your community and the wider world.",
            "Relate your interest to something the school has to offer/some reason why this school would be the best place for you to pursue it (For example, 'I believe Cornell’s Hospitality program will allow me to pursue my ambitions like no other because…')."
        ],
        "common_errors": [
            "Being too academic: Being specific is good! The best academic interest essays will focus on a specific niche, but you need to be careful not to ramble or get too technical to the point the essay reader can’t follow."
        ]
    },
    "Other": {
        "keywords": [],
        "examples": [],
        "overview": "This category includes prompts that don't fit into the other defined categories.",
        "suggestions": [],
        "common_errors": []
    }
}


def classify_prompt(prompt):
    # Improved classification based on keyword matching
    prompt_lower = prompt.lower()
    for category, data in categories.items():
        for keyword in data["keywords"]:
            if keyword in prompt_lower:
                return category
    return "Other"

@app.route('/health', methods=['GET'])
def health_check():
    return "OK", 200

@app.route('/analyze', methods=['POST'])
def analyze_text():
    try:
        prompt = request.json['prompt']
        essay = request.json['essay']
        logging.info(f"Received request with prompt: {prompt[:50]}...")

        # Classify the prompt
        category = classify_prompt(prompt)
        logging.info(f"Prompt classified as: {category}")

        # Get category-specific overview, suggestions, and common errors
        overview = categories[category]["overview"]
        suggestions = categories[category]["suggestions"]
        common_errors = categories[category]["common_errors"]

        # Perform the essay analysis
        analysis = get_gpt_analysis(prompt, essay, overview, suggestions, common_errors, category)
        logging.info("Analysis completed successfully")
        return jsonify(analysis)
    except Exception as e:
        logging.error(f"Error in analyze_text: {str(e)}")
        return jsonify({"error": str(e)}), 500

def get_gpt_analysis(prompt, essay, overview, suggestions, common_errors, category):
    system_message = f"""You are a College counselor and a writing assistant. Your task is to analyze the given essay based on the provided prompt.
    Provide detailed feedback on the essay's structure, content, grammar, spelling, punctuation, and relevance to the prompt.
    Offer specific suggestions for improvement and identify precise locations of errors with clear corrections. Your response should be in a structured format for easy parsing.

    Overview: {overview}
    Suggestions: {suggestions}
    Common Errors: {common_errors}
    """

    user_message = f"""Prompt: {prompt}
Essay:
{essay}
Analyze the essay and provide a response in the following JSON format:
{{
    "category": "{category}",
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
