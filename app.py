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

DB_PATH = ':memory:'
_db_conn = None

def get_db():
    global _db_conn
    if _db_conn is None:
        _db_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return _db_conn

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
    if row:
        user_id, name = row[0], row[1]
    else:
        name = email.split('@')[0]
        cursor.execute("INSERT INTO users (id, email, name) VALUES (?, ?, ?)", (user_id, email, name))
        conn.commit()
    login_user(User(user_id, email, name))
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
    return safe_render('dashboard.html', ppts=user_ppts)

# STAGE 1: Generate the Slides Outline Layout Structure
@app.route('/generate/outline', methods=['POST'])
@login_required
def generate_outline():
    prompt = request.form.get('prompt')
    theme = request.form.get('theme', 'modern')
    
    if not prompt:
        return "Please input a topic description.", 400
        
    outline_instruction = (
        "You are an academic presentation planner. Analyze the user's prompt topic and plan a comprehensive slide layout. "
        "Return a valid JSON object containing a 'title' string and an array named 'outline' consisting of 4 to 6 slide heading strings. "
        "Do not include markdown wrappers or backticks. Example structure: "
        "{\"title\": \"Topic Title\", \"outline\": [\"Slide 1 Heading\", \"Slide 2 Heading\"]}"
    )
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
        response = model.generate_content(f"{outline_instruction}\n\nUser prompt: {prompt}")
        data = json.loads(response.text.strip())
    except Exception as e:
        data = {
            "title": prompt.title(),
            "outline": ["1. Introduction & Background", "2. Core Mechanisms & Definitions", "3. Practical Implementations", "4. Summary Conclusion"]
        }
        
    return safe_render('outline.html', title=data.get('title', prompt), headings=data.get('outline', []), original_prompt=prompt, theme=theme)

# STAGE 2: Deeply research and pull heavy information for each individual heading
@app.route('/generate/final', methods=['POST'])
@login_required
def generate_final():
    prompt = request.form.get('original_prompt')
    title = request.form.get('title')
    theme = request.form.get('theme')
    headings = request.form.getlist('headings')
    
    slides_data = []
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    for heading in headings:
        # We drop JSON format constraints here to let Gemini write rich, full text lengths easily
        content_instruction = (
            f"Provide an exhaustive, detailed academic research analysis about this slide heading: '{heading}'. "
            f"This slide is part of a presentation titled '{title}' on the topic '{prompt}'. "
            "Write 3 separate paragraphs of deep, detailed educational facts, concepts, definitions, or mechanisms. "
            "Each paragraph must be a complete, highly informative sentence. Do not write short phrases or restate the title. "
            "Separate each distinct point with a new line."
        )
        
        try:
            response = model.generate_content(content_instruction)
            text_lines = response.text.strip().split('\n')
            # Filter out empty entries, asterisks, or blank lines
            bullets = [line.replace('*', '').strip() for line in text_lines if len(line.strip()) > 15]
            
            # If the response array parsed too short, build structured fallbacks
            if len(bullets) < 2:
                bullets = [
                    f"Foundational framework analysis regarding {heading} mechanics.",
                    "Comprehensive operational overview detailing specific structural data variables.",
                    "Practical field case study metrics and analytical summary review."
                ]
        except Exception:
            bullets = [
                f"Foundational framework analysis regarding {heading} mechanics.",
                "Comprehensive operational overview detailing specific structural data variables.",
                "Practical field case study metrics and analytical summary review."
            ]
            
        slides_data.append({"heading": heading, "bullets": bullets[:4]})

    ppt_id = str(uuid.uuid4())[:8]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO presentations (ppt_id, user_id, prompt, title, content_json, theme, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (ppt_id, current_user.id, prompt, title, json.dumps(slides_data), theme, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    
    return redirect(url_for('view_presentation', ppt_id=ppt_id))

@app.route('/presentation/<ppt_id>')
@login_required
def view_presentation(ppt_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT title, content_json, theme FROM presentations WHERE ppt_id = ? AND user_id = ?", (ppt_id, current_user.id))
    row = cursor.fetchone()
    if not row:
        return "Presentation structure not found.", 404
    return safe_render('view_ppt.html', title=row[0], slides=json.loads(row[1]), theme=row[2])

init_db()
if __name__ == '__main__':
    app.run(debug=True)
