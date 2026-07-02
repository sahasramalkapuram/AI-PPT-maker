import os
import json
import io
from flask import Flask, render_template, request, redirect, url_for, send_file
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

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
            "title": f"Slide {i+1}: Analytical Review on {prompt.strip() or 'Your Topic'}",
            "bullets": [
                f"Primary parameter data metrics tracking foundational structural parameters {i+1}.",
                "Secondary logical execution metric isolating the core performance vectors.",
                "Granular takeaway summarizing the operational context payload delivery layers."
            ],
            "image_query": f"abstract tech structure {i}" if assets_config in ['both', 'images'] else None,
            "chart_data": [15, 30, 45, i * 10 + 20] if assets_config in ['both', 'charts'] else None
        }
        slides.append(slide_data)
    return slides

# 1. Main Home Route Redirect Fix
@app.route('/')
def home():
    return redirect(url_for('dashboard'))

# 2. Workspace Control Dashboard
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# 3. Slide Generation Engine Route
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

# 4. PowerPoint Document Builder Export Route
@app.route('/export/pptx', methods=['POST'])
def export_pptx():
    try:
        slides_data_raw = request.form.get('slides_json', '[]')
        slides_list = json.loads(slides_data_raw)
        
        prs = Presentation()
        
        for slide_item in slides_list:
            blank_slide_layout = prs.slide_layouts[6] 
            slide = prs.slides.add_slide(blank_slide_layout)
            
            # Slide Dark-Theme Styling Background Color Layout
            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = RGBColor(15, 23, 42) # Slate-950 Dark theme match
            
            # Slide Title Text Box
            title_box = slide.shapes.add_textbox(Inches(0.75), Inches(0.5), Inches(8.5), Inches(1.0))
            tf_title = title_box.text_frame
            p_title = tf_title.paragraphs[0]
            p_title.text = slide_item.get('title', 'Presentation Slide')
            p_title.font.size = Pt(28)
            p_title.font.bold = True
            p_title.font.color.rgb = RGBColor(255, 255, 255)
            
            # Content Bullets Text Box Placement
            content_box = slide.shapes.add_textbox(Inches(0.75), Inches(1.8), Inches(5.5), Inches(4.5))
            tf_content = content_box.text_frame
            tf_content.word_wrap = True
            
            for index, bullet_text in enumerate(slide_item.get('bullets', [])):
                p_bullet = tf_content.add_paragraph() if index > 0 else tf_content.paragraphs[0]
                p_bullet.text = f"• {bullet_text}"
                p_bullet.font.size = Pt(14)
                p_bullet.font.color.rgb = RGBColor(203, 213, 225)
                p_bullet.space_after = Pt(12)

            # Sidebar Asset Frame Placeholder Block Mapping
            if slide_item.get('chart_data') or slide_item.get('image_query'):
                asset_box = slide.shapes.add_textbox(Inches(6.5), Inches(2.0), Inches(3.0), Inches(4.0))
                tf_asset = asset_box.text_frame
                tf_asset.word_wrap = True
                p_asset = tf_asset.paragraphs[0]
                p_asset.text = "📊 [Visual Asset Component Frame Location]"
                p_asset.font.size = Pt(12)
                p_asset.font.italic = True
                p_asset.font.color.rgb = RGBColor(129, 140, 248) # Indigo indicator tag
                
        # Compress Presentation file structure directly to an active stream memory block
        binary_output = io.BytesIO()
        prs.save(binary_output)
        binary_output.seek(0)
        
        return send_file(
            binary_output,
            mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            as_attachment=True,
            download_name="AI_Presentation_Deck.pptx"
        )
    except Exception as e:
        return f"PPTX Engine Export Bug Encountered: {str(e)}", 500

# Server Starter Hook Hook
if __name__ == '__main__':
    app.run(debug=True)
