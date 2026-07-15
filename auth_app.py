#!/usr/bin/env python3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-mandy')

# Use PostgreSQL on Railway (DATABASE_URL), fallback to SQLite locally
database_url = os.environ.get('DATABASE_URL', 'sqlite:///mandy.db')
# Railway provides postgres:// but SQLAlchemy needs postgresql://
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    api_key = db.Column(db.String(255), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if not username or not email or not password:
            return jsonify({'error': 'All fields required'}), 400

        if password != confirm:
            return jsonify({'error': 'Passwords do not match'}), 400

        if len(password) < 6:
            return jsonify({'error': 'Password must be 6+ characters'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username taken'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400

        user = User(username=username, email=email)
        user.set_password(password)
        user.api_key = secrets.token_urlsafe(32)
        db.session.add(user)
        db.session.commit()

        return jsonify({'success': 'Account created! Login now.', 'redirect': url_for('login')}), 201

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401

        session['user_id'] = user.id
        session['username'] = user.username

        return jsonify({'success': 'Logged in!', 'redirect': url_for('dashboard')}), 200

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/settings')
@login_required
def settings():
    user = User.query.get(session['user_id'])
    return render_template('settings.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/user')
@login_required
def api_user():
    user = User.query.get(session['user_id'])
    return jsonify({'username': user.username, 'email': user.email, 'api_key': user.api_key})

@app.route('/api/generate-key', methods=['POST'])
@login_required
def generate_key():
    user = User.query.get(session['user_id'])
    user.api_key = secrets.token_urlsafe(32)
    db.session.commit()
    return jsonify({'api_key': user.api_key})

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    try:
        from groq import Groq
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400

        user_message = data['message'].strip()
        history = data.get('history', [])

        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400

        api_key = os.environ.get('GROQ_API_KEY')
        if not api_key:
            return jsonify({'error': 'GROQ_API_KEY not configured on the server.'}), 500

        client = Groq(api_key=api_key)

        username = session.get('username', 'User')
        system_prompt = (
            f"You are MANDY, a powerful personal AI assistant. "
            f"You are talking to {username}. "
            "Be helpful, concise, and friendly. You can help with tasks, answer questions, "
            "write code, summarize information, and much more. "
            "Use markdown formatting in your responses where appropriate."
        )

        messages = [{"role": "system", "content": system_prompt}]

        # Add previous conversation history (last 20 messages max)
        for msg in history[-20:]:
            if msg.get('role') in ('user', 'assistant') and msg.get('content'):
                messages.append({"role": msg['role'], "content": msg['content']})

        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=1024,
        )

        reply = response.choices[0].message.content
        return jsonify({'reply': reply}), 200

    except Exception as e:
        return jsonify({'error': f'AI error: {str(e)}'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)