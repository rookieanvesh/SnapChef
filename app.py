import os
import requests
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
from twilio.rest import Client
from PIL import Image

# Load environment variables
load_dotenv()

# Initialize Flask
app = Flask(__name__)

# Configure APIs
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

def get_recipes(ingredients):
    """Get recipes using Spoonacular API"""
    try:
        # Get recipe suggestions
        recipe_params = {
            "ingredients": ",".join(ingredients[:5]),  # Use top 5 ingredients
            "number": 2,  # Get 2 recipes
            "apiKey": os.getenv("SPOONACULAR_API_KEY")
        }
        recipe_response = requests.get(
            "https://api.spoonacular.com/recipes/findByIngredients",
            params=recipe_params
        )
        recipes = recipe_response.json()

        # Format recipes for WhatsApp
        recipe_text = "\n\n🍴 *Suggested Recipes:*\n"
        for recipe in recipes:
            # Get detailed instructions
            detail_response = requests.get(
                f"https://api.spoonacular.com/recipes/{recipe['id']}/information",
                params={"apiKey": recipe_params["apiKey"]}
            )
            details = detail_response.json()
            
            recipe_text += (
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔹 *{recipe['title']}*\n"
                f"⏱️ Ready in {details.get('readyInMinutes', 'N/A')} mins\n"
                f"🔗 {details.get('sourceUrl', 'View instructions in app')}\n"
            )
        
        return recipe_text
    
    except Exception as e:
        print(f"Recipe Error: {str(e)}")
        return "\n\n🚫 Couldn't fetch recipes right now"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_image():
    try:
        # Get phone number from form
        phone_number = request.form.get('phone')
        if not phone_number.startswith('+'):
            return jsonify({"error": "Phone number must include country code (e.g., +91)"}), 400
        # Get and analyze image
        img_file = request.files['image']
        img = Image.open(img_file)
        
        # Gemini analysis
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([
            "List all food ingredients in this fridge photo. Return ONLY comma-separated items, no explanations.",
            img
        ])
        ingredients = [i.strip() for i in response.text.split(",")]
        print("Detected Ingredients:", ingredients)

        # Get recipes
        recipe_text = get_recipes(ingredients)

        # Create WhatsApp message
        message = (
            "🛒 *Your Smart Grocery List:*\n"
            f"{', '.join(ingredients)}\n"
            f"{recipe_text}\n\n"
            "🔍 _Powered by SnapChef AI_"
        )

        # Send via WhatsApp
        twilio_client.messages.create(
            body=message,
            from_=f'whatsapp:{twilio_whatsapp_number}',
            to=f'whatsapp:{phone_number}'
        )

        return jsonify({
            "message": "Recipes sent to WhatsApp!",
            "ingredients": ingredients
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)