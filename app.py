from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
import jwt
import datetime
from functools import wraps
import os
import csv
import re as r
from urllib.request import urlopen
from questiongenerator import QuestionGenerator
from fpdf import FPDF
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yoursecretkey'

# Generate RSA keys
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
public_key = private_key.public_key()

# Serialize the keys
private_key_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
)
public_key_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

# Initialize question generator
qg = QuestionGenerator()

# JWT decorator to protect routes
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('jwt_token')
        if not token:
            return redirect(url_for('login'))
        try:
            jwt.decode(token, public_key_pem, algorithms=['RS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 403
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 403
        return f(*args, **kwargs)
    return decorated

# Function to generate questions and clean up special tokens
def generate_questions(article, num_que):
    result = ''
    if article.strip():
        if num_que is None or num_que == '':
            num_que = 3
        else:
            num_que = num_que
        
        # Generate the questions
        generated_questions_list = qg.generate(article, num_questions=int(num_que))
        
        # Remove special tokens like <pad> and </s> from the generated questions and add numbering
        cleaned_questions = []
        for i, question in enumerate(generated_questions_list, start=1):
            question = question.replace("<pad>", "").replace("</s>", "").strip()  # Removing <pad> and </s> tokens
            if not question.endswith('?'):
                question += '?'  # Add '?' only if it doesn't already end with one
            cleaned_questions.append(f"{i}. {question}")  # Adding numbering
        
        # Join the cleaned and numbered questions for output
        result = '\n'.join(cleaned_questions)
        return result
    else:
        return "Please provide text for generating questions."

# Function to save output as a PDF file
def save_output_as_pdf(text_data, filename="generated_questions.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in text_data.split('\n'):
        pdf.cell(200, 10, txt=line, ln=True)
    pdf.output(filename)
    return filename

# Login route
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Dummy authentication for demonstration
        if username == 'user' and password == 'password':
            token = jwt.encode({
                'user': username,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
            }, private_key_pem, algorithm='RS256')

            # Set JWT as a cookie
            response = redirect(url_for('home'))
            response.set_cookie('jwt_token', token, httponly=True)
            return response
        else:
            return jsonify({'message': 'Invalid credentials!'}), 401

    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    response = jsonify({'message': 'Logged out successfully'})
    response.set_cookie('jwt_token', '', expires=0)
    return response

# Home (protected) route - the main app functionality
@app.route('/dashboard', methods=['GET', 'POST'])
@token_required
def home():
    if request.method == 'POST':
        article = request.form['article']
        num_questions = request.form['num_questions']

        # Generate the questions
        generated_questions = generate_questions(article, num_questions)

        # Save output to a PDF file
        pdf_filename = save_output_as_pdf(generated_questions)

        return render_template('dashboard.html', article=article, num_questions=num_questions, generated_questions=generated_questions, pdf_filename=pdf_filename)
    
    return render_template('dashboard.html', article="", num_questions=3, generated_questions="", pdf_filename="")

# Route to download the generated PDF
@app.route('/download/<filename>')
@token_required
def download_file(filename):
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
