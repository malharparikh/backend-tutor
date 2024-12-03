from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from gpt_analysis import get_gpt_analysis
from prompt_classifier import classify_prompt
from categories import categories

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize Firebase Admin SDK
cred = credentials.Certificate('edvize-server-firebase-adminsdk-gib5t-7647fa9821.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# Firestore Collections and References
users_ref = db.collection('users')

def check_or_initialize_payment(user_id):
    """Check or initialize the payment document for a user."""
    payment_ref = users_ref.document(user_id).collection('payment').document('details')
    payment_doc = payment_ref.get()

    if not payment_doc.exists:
        # Initialize payment document with default values
        payment_ref.set({
            'token_count': 1,
            'is_subscribed': False,
            'subscription_end_date': None
        })
        return {'token_count': 1, 'is_subscribed': False}
    else:
        return payment_doc.to_dict()

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
        user_id = data.get('userId')
        prompt = data.get('prompt')
        essay = data.get('essay')

        if not user_id or not prompt or not essay:
            return jsonify({"error": "Missing 'user_id', 'prompt', or 'essay' in the request"}), 400

        logging.info(f"Received request with prompt: {prompt[:50]}...")

        # Check or initialize payment document
        payment_details = check_or_initialize_payment(user_id)
        token_count = payment_details['token_count']
        is_subscribed = payment_details['is_subscribed']

        # Verify tokens or subscription
        tokens_required = 1
        if not is_subscribed and token_count < tokens_required:
            return jsonify({"error": "Insufficient tokens. Please purchase tokens or subscribe."}), 403

        # Deduct tokens if not subscribed
        if not is_subscribed:
            new_token_count = token_count - tokens_required
            users_ref.document(user_id).collection('payment').document('details').update({
                'token_count': new_token_count
            })

        # Classify the prompt
        category = classify_prompt(prompt)
        if category not in categories:
            return jsonify({"error": f"Category '{category}' not found in the categories"}), 500

        # Perform the essay analysis
        analysis = get_gpt_analysis(prompt, essay, category)
        if "error" in analysis:
            return jsonify(analysis), 500

        logging.info("Analysis completed successfully")
        return jsonify(analysis)
    except Exception as e:
        logging.error(f"Error in analyze_text: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/save-draft', methods=['POST'])
def save_draft():
    try:
        data = request.json
        user_id = data['user_id']
        draft_id = data.get('draft_id', None)
        prompt = data['prompt']
        essay = data['essay']
        status = data['status']
        university = data['university']
        wordCount = data['wordCount']

        # Check or initialize payment document
        check_or_initialize_payment(user_id)

        drafts_ref = users_ref.document(user_id).collection('drafts')
        if draft_id:  # Update existing draft
            draft_ref = drafts_ref.document(draft_id)
            draft_ref.set({
                'prompt': prompt,
                'essay': essay,
                'status': status,
                'university': university,
                'wordCount': wordCount
            }, merge=True)
        else:  # Create new draft
            _, draft_ref = drafts_ref.add({
                'prompt': prompt,
                'essay': essay,
                'status': status,
                'university': university,
                'wordCount': wordCount
            })
            draft_id = draft_ref.id

        return jsonify({"success": True, "message": "Draft saved successfully", "draft_id": draft_id}), 200
    except Exception as e:
        logging.error(f"Error in save_draft: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/get-draft', methods=['GET'])
def get_draft():
    try:
        user_id = request.args.get('user_id')
        draft_id = request.args.get('draft_id')

        if not user_id or not draft_id:
            return jsonify({"success": False, "message": "user_id and draft_id are required"}), 400

        # Check or initialize payment document
        check_or_initialize_payment(user_id)

        draft_ref = users_ref.document(user_id).collection('drafts').document(draft_id)
        draft = draft_ref.get()
        if draft.exists:
            return jsonify({"success": True, "draft": draft.to_dict()}), 200
        else:
            return jsonify({"success": False, "message": "Draft not found"}), 404
    except Exception as e:
        logging.error(f"Error in get_draft: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    
# Route to Get All Drafts by user_id
@app.route('/get-all-drafts', methods=['GET'])
def get_all_drafts():
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"success": False, "message": "user_id is required"}), 400
        
        check_or_initialize_payment(user_id)
        
        # Reference to the user's drafts collection
        drafts_ref = users_ref.document(user_id).collection('drafts')
        drafts = drafts_ref.stream()
        
        all_drafts = [{draft.id: {**draft.to_dict(), 'draft_id': draft.id}} for draft in drafts]
        
        return jsonify({"success": True, "drafts": all_drafts}), 200
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/update-tokens', methods=['POST'])
def update_tokens():
    """
    API to deduct 1 token for a user only if not subscribed.
    """
    try:
        data = request.json
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"success": False, "message": "user_id is required"}), 400

        payment_ref = users_ref.document(user_id).collection('payment').document('details')

        # Fetch the existing payment document
        payment_doc = payment_ref.get()
        if not payment_doc.exists:
            return jsonify({"success": False, "message": "Payment document not found"}), 404

        payment_data = payment_doc.to_dict()
        token_count = payment_data.get('token_count', 0)
        is_subscribed = payment_data.get('is_subscribed', False)

        # Check if the user is subscribed
        if is_subscribed:
            return jsonify({"success": False, "message": "User is subscribed; no tokens deducted"}), 200

        # Deduct 1 token if user has enough tokens
        if token_count > 0:
            payment_ref.update({'token_count': token_count - 1})
            return jsonify({"success": True, "message": "Token deducted successfully", "new_token_count": token_count - 1}), 200
        else:
            return jsonify({"success": False, "message": "Insufficient tokens"}), 400

    except Exception as e:
        logging.error(f"Error in update_tokens: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/add-tokens', methods=['POST'])
def add_tokens():
    """
    API to add tokens for a user.
    """
    try:
        data = request.json
        user_id = data.get('user_id')
        tokens_to_add = data.get('token_count')

        if not user_id:
            return jsonify({"success": False, "message": "user_id is required"}), 400

        if tokens_to_add is None or tokens_to_add <= 0:
            return jsonify({"success": False, "message": "token_count must be a positive integer"}), 400

        payment_ref = users_ref.document(user_id).collection('payment').document('details')

        # Fetch the existing payment document
        payment_doc = payment_ref.get()
        if not payment_doc.exists:
            return jsonify({"success": False, "message": "Payment document not found"}), 404

        payment_data = payment_doc.to_dict()
        token_count = payment_data.get('token_count', 0)

        # Add tokens to the existing token count
        new_token_count = token_count + tokens_to_add
        payment_ref.update({'token_count': new_token_count})

        return jsonify({"success": True, "message": f"{tokens_to_add} tokens added successfully", "new_token_count": new_token_count}), 200

    except Exception as e:
        logging.error(f"Error in add_tokens: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/get-tokens', methods=['GET'])
def get_tokens():
    """
    API to fetch token count and subscription details for a user.
    """
    try:
        user_id = request.args.get('user_id')

        if not user_id:
            return jsonify({"success": False, "message": "user_id is required"}), 400

        payment_ref = users_ref.document(user_id).collection('payment').document('details')

        # Fetch the payment document
        payment_doc = payment_ref.get()
        if not payment_doc.exists:
            return jsonify({"success": False, "message": "Payment document not found"}), 404

        # Return the payment details
        payment_details = payment_doc.to_dict()
        return jsonify({"success": True, "payment_details": payment_details}), 200

    except Exception as e:
        logging.error(f"Error in get_tokens: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
