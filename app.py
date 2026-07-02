import os
from flask import Flask, render_template, request, redirect, url_for, flash

# Initialize Flask and explicitly define the template directory folder
app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-12345")

def generate_ai_slides(prompt, count, assets_config):
    """
    Generates structured slide content matching the configuration parameters.
    """
    slides = []
    for i in range(int(count)):
        slide_data = {
            "title": f"Slide {i+1}: Core Analysis of {prompt.strip() or 'Your Topic'}",
            "bullets": [
                f"Primary analytical dimension tracking framework requirements for slide layout configuration {i+1}.",
                "Secondary logical execution parameter parsing the contextual data streams cleanly.",
                "Granular takeaway summarizing the operational performance and impact metrics."
            ],
            "image_query": f"technology abstract orientation {i}" if assets_config in ['both', 'images'] else None,
            "chart_data": [12, 28, 40, i * 12 + 20] if assets_config in ['both', 'charts'] else None
        }
        slides.append(slide_data)
    return slides

# 1. Main Home Route Redirect Fix
@app.route('/')
def home():
    return redirect(url_for('dashboard'))

# 2. Workspace Control Dashboard (Bypasses all broken login context processors)
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# 3. Slide Generation Engine Route
@app.route('/generate/outline', methods=['POST'])
def generate_outline():
    try:
        # Safely extract form values from the dashboard frontend UI
        prompt = request.form.get('prompt', '').strip()
        aesthetic = request.form.get('aesthetic', 'cyberpunk')
        slide_count = request.form.get('slide_count', '7')
        assets = request.form.get('assets', 'both')
        
        if not prompt:
            return redirect(url_for('dashboard'))
            
        # Build the mock data deck
        generated_deck = generate_ai_slides(prompt, slide_count, assets)
        
        # Render the preview outline template
        return render_template(
            'outline.html', 
            slides=generated_deck, 
            aesthetic=aesthetic,
            prompt=prompt
        )
        
    except Exception as e:
        return f"Internal Processing Error: {str(e)}", 500

# Server starter execution hook (Must be at the absolute bottom of the file)
if __name__ == '__main__':
    app.run(debug=True)
