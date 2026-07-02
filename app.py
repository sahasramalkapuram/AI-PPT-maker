import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_required, current_user

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-dev-key-12345")

# Initialize Login Manager (Ensure this matches your configuration)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Dummy or Mock Slide Engine Generation for safety verification
def generate_ai_slides(prompt, count, assets_config):
    """
    Simulates structured slide distribution arrays matching template parameters.
    """
    slides = []
    for i in range(int(count)):
        slide_data = {
            "title": f"Slide {i+1}: Analytical Deep-Dive on {prompt.strip() or 'Topic'}",
            "bullets": [
                f"Core foundational concept indicator number {i+1} regarding structural patterns.",
                "Secondary logical execution metric parsing structural parameters dynamically.",
                "Granular takeaway summarizing the core context payload layer."
            ],
            "image_query": f"quantum physics abstract {i}" if assets_config in ['both', 'images'] else None,
            "chart_data": [10, 24, 45, i * 15 + 20] if assets_config in ['both', 'charts'] else None
        }
        slides.append(slide_data)
    return slides

@app.route('/dashboard')
@login_required
def dashboard():
    # Renders the beautiful custom control panel
    return render_template('dashboard.html')

@app.route('/generate/outline', methods=['POST'])
@login_required  # Protects route safely within user session context
def generate_outline():
    try:
        # 1. Safely extract values from form inputs
        prompt = request.form.get('prompt', '').strip()
        aesthetic = request.form.get('aesthetic', 'warm-terracotta')
        slide_count = request.form.get('slide_count', '7')
        assets = request.form.get('assets', 'both')
        
        if not prompt:
            flash("Please supply a baseline concept prompt or outline topic.", "error")
            return redirect(url_for('dashboard'))
            
        # 2. Invoke generation pipeline
        generated_deck = generate_ai_slides(prompt, slide_count, assets)
        
        # 3. Handoff contextual data variables directly to template engine
        return render_template(
            'outline.html', 
            slides=generated_deck, 
            aesthetic=aesthetic,
            prompt=prompt
        )
        
    except Exception as e:
        # Fallback system tracker to catch inner crashes safely
        app.logger.error(f"Execution Failure under generation step: {str(e)}")
        return f"Internal Processing Error: {str(e)}", 500
@app.route('/')
def home():
    # Automatically forward root visitors straight to the dashboard route
    return redirect(url_for('dashboard'))
if __name__ == '__main__':
    app.run(debug=True)
