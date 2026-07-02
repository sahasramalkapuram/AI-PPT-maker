from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import google.generativeai as genai
import sqlite3
import uuid
import os
import json
from datetime import datetime

app = Flask(__name__, template_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', '7ca46c82d8a64db9bd4e23cfb8a0df12')

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

DB_PATH = os.path.join(os.path.dirname(__file__), 'storage.db')

def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

class User(UserMixin):
    def __init__(self, id, email, name):
        self.id = id
        self.email = email
        self.name = name

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return User(row[0], row[1], row[2])
    return None

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE, name TEXT)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS presentations (
            ppt_id TEXT PRIMARY KEY,
            user_id TEXT,
            prompt TEXT,
            title TEXT,
            content_json TEXT,
            theme TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def safe_render(filename, **kwargs):
    possible_paths = [f"templates/{filename}", f"templates//{filename}", filename]
    for path in possible_paths:
        if os.path.exists(path):
            return render_template(path, **kwargs)
    return render_template(f"templates/{filename}", **kwargs)

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return safe_render('login.html')

@app.route('/login/email', methods=['POST'])
def login_email():
    email = request.form.get('email').strip().lower()
    user_id = str(uuid.uuid4())[:8]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (id, email, name) VALUES (?, ?, ?)", (user_id, email, email.split('@')[0]))
        conn.commit()
    else:
        user_id = row[0]
    conn.close()
    login_user(User(user_id, email, email.split('@')[0]))
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_page'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT ppt_id, title, prompt, theme, created_at FROM presentations WHERE user_id = ? ORDER BY created_at DESC", (current_user.id,))
    user_ppts = [{ 'id': r[0], 'title': r[1], 'prompt': r[2], 'theme': r[3], 'date': r[4] } for r in cursor.fetchall()]
    conn.close()
    return safe_render('dashboard.html', ppts=user_ppts)

@app.route('/generate/outline', methods=['POST'])
@login_required
def generate_outline():
    prompt = request.form.get('prompt')
    theme = request.form.get('theme', 'modern')
    slide_count = request.form.get('slide_count', '5')
    content_length = request.form.get('content_length', 'detailed')
    include_visuals = request.form.get('include_visuals', 'none')
    
    if not prompt:
        return "Please input a topic description.", 400
        
    ai_heavy_instruction = (
        f"You are an expert presentation builder. Build a structured deck based on the prompt topic. "
        f"You MUST generate EXACTLY {slide_count} slide entries. "
        f"The content length parameter rules are: {content_length}. Ensure every single bullet point matches this length constraint description. "
        f"Visual settings requirement is: {include_visuals}. "
        "If visual settings require images, provide an 'image_query' string for that slide matching an absolute keyword description. "
        "If visual settings require charts, include a valid 'chart_data' dictionary containing 'labels' (array) and 'data' (array of numeric metric values). Otherwise leave them blank. "
        "Your response MUST be entirely valid raw JSON data matching this exact schema block without backticks: "
        "{\"title\": \"Main Topic\", \"slides\": [{\"heading\": \"Slide Title\", \"bullets\": [\"Detailed fact 1.\"], \"image_query\": \"animals\", \"chart_data\": {\"labels\": [\"A\",\"B\"], \"data\": [40,60]}}]}"
    )
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
        response = model.generate_content(f"{ai_heavy_instruction}\n\nUser prompt: {prompt}")
        data = json.loads(response.text.strip())
    except Exception as e:
        data = {
            "title": prompt.title(),
            "slides": [{"heading": "Introduction Framework", "bullets": ["Fallback basic conceptual overview criteria entry."], "image_query": "nature", "chart_data": {}}]
        }
        
    session['temp_ppt_data'] = data
    session['temp_prompt'] = prompt
    session['temp_theme'] = theme
    
    return safe_render('outline.html', title=data.get('title', prompt), slides=data.get('slides', []), original_prompt=prompt, theme=theme)

@app.route('/generate/final', methods=['POST'])
@login_required
def generate_final():
    prompt = session.get('temp_prompt', 'AI Slide Deck')
    theme = session.get('temp_theme', 'modern')
    title = request.form.get('title')
    headings = request.form.getlist('headings')
    
    final_slides = []
    for idx, heading in enumerate(headings):
        bullets = request.form.getlist(f'bullets_slide_{idx}')
        img_q = request.form.get(f'image_query_{idx}', '')
        c_labels = request.form.get(f'chart_labels_{idx}', '')
        c_data = request.form.get(f'chart_data_{idx}', '')
        
        chart_dict = {}
        if c_labels and c_data:
            try:
                chart_dict = {"labels": json.loads(c_labels), "data": json.loads(c_data)}
            except:
                pass

        final_slides.append({
            "heading": heading,
            "bullets": [b.strip() for b in bullets if b.strip()],
            "image_query": img_q.strip(),
            "chart_data": chart_dict
        })

    ppt_id = str(uuid.uuid4())[:8]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO presentations (ppt_id, user_id, prompt, title, content_json, theme, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (ppt_id, current_user.id, prompt, title, json.dumps(final_slides), theme, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    
    session.pop('temp_ppt_data', None)
    return redirect(url_for('view_presentation', ppt_id=ppt_id))

@app.route('/presentation/<ppt_id>')
@login_required
def view_presentation(ppt_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT title, content_json, theme FROM presentations WHERE ppt_id = ? AND user_id = ?", (ppt_id, current_user.id))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "Presentation structure not found.", 404
    return safe_render('view_ppt.html', title=row[0], slides=json.loads(row[1]), theme=row[2])

init_db()
if __name__ == '__main__':
    app.run(debug=True)
