import os
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-12345")

def generate_ai_slides(prompt, count, assets_config):
    """
    Simulates dynamic AI slide generation with smart asset placement,
    varied content lengths, and high-fidelity topic variations.
    """
    slides = []
    
    # Topic-specific contextual anchors for realistic, dynamic image lookups
    sample_contexts = [
        {"aspect": "Conceptual Foundations", "img_term": "macro photography crisp realism physics", "has_chart": False},
        {"aspect": "Statistical Metrics & Data", "img_term": "clean data office workspace 8k", "has_chart": True},
        {"aspect": "Practical Core Application", "img_term": "realistic industrial engineering machinery", "has_chart": False},
        {"aspect": "Future Strategic Horizon", "img_term": "high resolution laboratory research space", "has_chart": True},
        {"aspect": "Comparative Case Evaluation", "img_term": "detailed architecture building daylight", "has_chart": False},
    ]
    
    for i in range(int(count)):
        ctx = sample_contexts[i % len(sample_contexts)]
        
        # Decide if this slide needs a chart based on context and configuration settings
        show_chart = ctx["has_chart"] if assets_config in ['both', 'charts'] else False
        show_image = True if assets_config in ['both', 'images'] else False
        
        # Varying content styles: some slides use structured blocks, others use clean text narratives
        use_paragraph = (i % 2 == 1) 
        
        slide_data = {
            "title": f"Slide {i+1}: {ctx['aspect']} of {prompt.strip()}",
            "use_paragraph": use_paragraph,
            "paragraph_text": f"This layer outlines the definitive structural execution vectors underlying {prompt}. It represents a critical milestone in performance observation, synthesizing modern technical protocols with validated operational benchmarks established across empirical case studies.",
            "bullets": [
                f"Core execution protocol mapping key parameters for variable segment {i+1}.",
                "Resource allocation threshold calculated against real-time throughput metrics.",
                "Primary deployment optimization layer ensuring reliable output scaling."
            ],
            # Uses a dynamic search term directly inside Unsplash's source engine for realism
            "image_query": f"https://images.unsplash.com/photo-1506318137071-a8e063b4bec0?auto=format&fit=crop&w=600&q=80" if show_image and i==0 else None,
            "chart_data": [25, 45, i * 10 + 30, 85] if show_chart else None,
            "img_keyword": f"{prompt.strip()} {ctx['img_term']}" if show_image else None
        }
        
        # Inject realistic image variations using diverse high-quality stock indexes
        if show_image:
            img_ids = [
                "photo-1451187580459-43490279c0fa", # Quantum Tech
                "photo-1551288049-bebda4e38f71", # Clean Analytics chart screen
                "photo-1486406146926-c627a92ad1ab", # High-rise architecture
                "photo-1507413245164-6160d8298b31", # High-end Lab environment
                "photo-1461749280684-dccba630e2f6"  # Precision tech workspace
            ]
            slide_data["image_url"] = f"https://images.unsplash.com/{img_ids[i % len(img_ids)]}?auto=format&fit=crop&w=600&q=80"
            
        slides.append(slide_data)
        
    return slides

@app.route('/')
def home():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/generate/outline', methods=['POST'])
def generate_outline():
    try:
        prompt = request.form.get('prompt', '').strip()
        aesthetic = request.form.get('aesthetic', 'cyberpunk')
        slide_count = request.form.get('slide_count', '7')
        assets = request.form.get('assets', 'both')
        
        if not prompt:
            return redirect(url_for('dashboard'))
            
        generated_deck = generate_ai_slides(prompt, slide_count, assets)
        
        return render_template(
            'outline.html', 
            slides=generated_deck, 
            aesthetic=aesthetic,
            prompt=prompt
        )
    except Exception as e:
        return f"Internal Processing Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
