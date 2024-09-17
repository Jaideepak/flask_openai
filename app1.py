from flask import Flask, request, render_template, send_file
import os
import csv
import re as r
from urllib.request import urlopen
from questiongenerator import QuestionGenerator
from fpdf import FPDF

app = Flask(__name__)

qg = QuestionGenerator()

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

# Flask route for home page
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        article = request.form['article']
        num_questions = request.form['num_questions']

        # Generate the questions
        generated_questions = generate_questions(article, num_questions)

        # Save output to a PDF file
        pdf_filename = save_output_as_pdf(generated_questions)

        return render_template('index.html', article=article, num_questions=num_questions, generated_questions=generated_questions, pdf_filename=pdf_filename)
    
    return render_template('index.html', article="", num_questions=3, generated_questions="", pdf_filename="")

# Route to download the generated PDF
@app.route('/download/<filename>')
def download_file(filename):
    return send_file(filename, as_attachment=True)

# Run Flask app
if __name__ == "__main__":
    app.run(debug=True)
