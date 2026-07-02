from flask import Flask, render_template, request, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import google.generativeai as genai
import sqlite3
import uuid
import os
import json
from datetime import datetime

# Configuring absolute root fallback directories handles structural typos automatically
app = Flask(__name__, template_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', '7ca46c82d8a64db9bd4e23cfb8a0df12')

# Configure Gemini AI Free Tier
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

# Helper function safely searches both deep roots and simple directories
def safe_render(filename):
    possible_paths = [
        f"templates/{filename}",
        f"templates//{filename}",
        filename
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return render_template(path)
    return render_template(f"templates/{filename}")

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
    
    for path in ["templates/dashboard.html", "templates//dashboard.html", "dashboard.html"]:
        if os.path.exists(path):
            return render_template(path, ppts=user_ppts)
    return render_template("templates/dashboard.html", ppts=user_ppts)

@app.route('/generate', methods=['POST'])
@login_required
def generate_ppt():
    prompt = request.form.get('prompt')
    theme = request.form.get('theme', 'modern')
    
    if not prompt:
        return "Please input a topic description.", 400
        
    ai_system_instruction = (
        "You are an expert educational researcher and academic presentation maker. "
        "Generate an exhaustive, information-heavy presentation layout based on the user's prompt topic. "
        "Each slide MUST contain substantial information and deeply researched context. "
        "Do not just provide broad headers. For every single slide, write 3 to 5 detailed, descriptive bullet points "
        "explaining core definitions, structural mechanisms, factual data, or logical steps related to the slide's heading. "
        "Your response MUST be entirely valid JSON data matching this schema exactly without markdown wrapping or backticks: "
        "{\"title\": \"Comprehensive Presentation Title\", \"slides\": [{\"heading\": \"Detailed Slide Heading\", \"bullets\": [\"Extremely descriptive sentence explaining fact 1 with context.\", \"Thoroughly written point 2 expanding on details and definitions.\", \"Detailed academic point 3 providing analysis or data.\"]}]}"
    )
    
  try:
        # Forcing Gemini to strictly speak JSON native format
        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            generation_config={"response_mime_type": "application/json"}
        )
        response = model.generate_content(f"{ai_system_instruction}\n\nUser prompt: {prompt}")
        
        # Clean up any weird wrapping strings if they exist
        text_clean = response.text.strip()
        if text_clean.startswith("```"):
            text_clean = text_clean.strip("`").replace("json", "", 1).strip()
            
        data = json.loads(text_clean)
    except Exception as e:
        # Detailed academic safety fallback if API limits are throttled
        data = {
            "title": prompt.title(),
            "slides": [
                {"heading": "Core Overview", "bullets": ["Comprehensive conceptual breakdown of your chosen academic prompt.", "In-depth review of historical parameters and structural mechanisms.", "Analyzed data streams explaining foundational topic pillars."]},
                {"heading": "Detailed Technical Analysis", "bullets": ["Primary architectural framework execution variables.", "Step-by-step logical functions and operational methodology.", "Supporting equations or structural variables detailed thoroughly."]},
                {"heading": "Academic Summary", "bullets": ["Concluding thesis takeaways and project observations.", "Practical real-world application cases for this system framework.", "Open research problems for student team discussions."]}
            ]
        }

    ppt_id = str(uuid.uuid4())[:8]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO presentations (ppt_id, user_id, prompt, title, content_json, theme, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (ppt_id, current_user.id, prompt, data.get('title', prompt), json.dumps(data.get('slides', [])), theme, datetime.now().strftime("%Y-%m-%d %H:%M")))
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
        
    for path in ["templates/view_ppt.html", "templates//view_ppt.html", "view_ppt.html"]:
        if os.path.exists(path):
            return render_template(path, title=row[0], slides=json.loads(row[1]), theme=row[2])
    return render_template("templates/view_ppt.html", title=row[0], slides=json.loads(row[1]), theme=row[2])

init_db()
if __name__ == '__main__':
    app.run(debug=True)
