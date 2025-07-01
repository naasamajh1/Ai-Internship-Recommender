import os
from dotenv import load_dotenv
load_dotenv()

import spacy
import sqlite3
import fitz  # PyMuPDF
import google.generativeai as genai
from flask import Flask, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Gemini Setup
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def extract_text_from_pdf(filepath):
    doc = fitz.open(filepath)
    return " ".join([page.get_text() for page in doc])

def classify_with_gemini(text):
    prompt = f"""You are an expert AI career advisor.

Here is a student's resume:

{text}

Please suggest the **top most suitable internship domains** for this student from the following:
🧠 Core Software Development Domains
Web Development

Front-End (HTML, CSS, JavaScript, React, etc.)

Back-End (Node.js, Django, Ruby on Rails, etc.)

Full-Stack

Mobile Development

Android (Kotlin/Java)

iOS (Swift)

Cross-platform (Flutter, React Native)

Desktop Application Development

Windows (C#, .NET)

macOS (Swift)

Cross-platform (Electron, Qt)

Game Development

Unity (C#)

Unreal Engine (C++)

Godot (GDScript)

Embedded Systems / IoT

C/C++ for microcontrollers

Raspberry Pi/Arduino

Real-Time Operating Systems (RTOS)

🧮 Specialized Technical Domains
DevOps & Infrastructure

CI/CD (Jenkins, GitHub Actions)

Containers (Docker, Kubernetes)

Cloud Platforms (AWS, Azure, GCP)

Data Engineering

ETL pipelines

Data Lakes & Warehouses

Tools: Apache Spark, Kafka

Machine Learning / AI

Data Science (Python, pandas, scikit-learn)

Deep Learning (TensorFlow, PyTorch)

MLOps

Cybersecurity

Penetration Testing

Secure Coding

Network Security

Blockchain / Web3

Smart Contracts (Solidity)

Decentralized Apps (DApps)

NFTs / Tokens

🛠️ Supportive & Emerging Domains
Software Testing & QA

Manual / Automated Testing

Tools: Selenium, Playwright, Cypress

UI/UX & Front-End Engineering

Accessibility, Design Systems

Tools: Figma, Tailwind, CSS-in-JS

AR/VR Development

Unity with XR

WebXR, OpenXR

Quantum Computing

Qiskit, Cirq, quantum algorithms

Low-code / No-code Platforms

Bubble, OutSystems, Webflow

🧾 Bonus: Business & Interdisciplinary Domains
Fintech

Payments, KYC, Fraud Detection

EdTech

E-learning platforms, gamification

HealthTech

Medical data handling, HIPAA compliance

E-commerce Development

Shopify, WooCommerce, custom carts

CRM / ERP Systems

Salesforce, SAP, Oracle

For each domain:
1. Give a short reason why it matches the student’s resume.
2. Suggest 2–3 specific ways the student can improve or prepare for that domain (e.g., topics to learn, projects to do, certifications, tools).

Format your response clearly like this:

Domain: <Domain Name>
Reason: <Reason>
Improvement Suggestions:
- Suggestion 1
- Suggestion 2
- Suggestion 3

Repeat this format for each of the 3 domains.
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# Feedback database
def init_db():
    with sqlite3.connect("feedback.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT,
                rating INTEGER,
                comment TEXT
            );
        """)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files["resume"]
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            resume_text = extract_text_from_pdf(filepath)
            gemini_response = classify_with_gemini(resume_text)

            # Parse Gemini response
            blocks = gemini_response.split("Domain:")
            recommendations = []

            for block in blocks[1:]:
                lines = block.strip().split("\n")
                domain = lines[0].strip()
                reason = ""
                improvements = []

                for line in lines[1:]:
                    if line.startswith("Reason:"):
                        reason = line.replace("Reason:", "").strip()
                    elif line.strip().startswith("-"):
                        improvements.append(line.replace("-", "").strip())

                recommendations.append({
                    "domain": domain,
                    "reason": reason,
                    "improvements": improvements
                })

            return render_template("result.html", recommendations=recommendations, resume_text=resume_text)

    return render_template("index_upload.html")

@app.route("/feedback", methods=["POST"])
def feedback():
    domain = request.form["domain"]
    rating = int(request.form["rating"])
    comment = request.form["comment"]

    with sqlite3.connect("feedback.db") as conn:
        conn.execute("INSERT INTO feedback (domain, rating, comment) VALUES (?, ?, ?)", (domain, rating, comment))

    return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
