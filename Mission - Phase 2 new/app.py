from flask import Flask, render_template, request, jsonify, redirect, url_for,session
from pymongo import MongoClient
from bson import ObjectId
import fitz  # PyMuPDF
# import pytesseract
from PIL import Image
import docx2txt
import io
import nltk
from textblob import TextBlob
#import matplotlib.pyplot as plt
import re

app = Flask(__name__)

app.secret_key = 'your_secret_key_here'

# MongoDB configuration
client = MongoClient('mongodb://localhost:27017')
db = client['parsed_content_db']
parsed_content_collection = db['parsed_content']

nltk.download('punkt')
nltk.download('stopwords')

# Define parsing functions
def parse_pdf(file):
    text_content = ""
    pdf_document = fitz.open(stream=io.BytesIO(file.read()))
    for page in pdf_document:
        text_content += page.get_text()
    return text_content



def parse_docx(file):
    text_content = docx2txt.process(io.BytesIO(file.read()))
    return text_content

def parse_document(file):
    if file.filename.lower().endswith('.pdf'):
        return parse_pdf(file)
    #elif file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        #return parse_image(file)
    elif file.filename.lower().endswith(('.doc', '.docx')):
        return parse_docx(file)
    else:
        raise ValueError("Unsupported file format")


@app.route("/")
def index():
    return render_template("login.html")

def extract_section_content(parsed_content, section_name):
    # Use regular expression to find the content between section headings
    pattern = re.compile(r'\b{}\b([\s\S]*?)(?=\b[A-Z][A-Z0-9\s]+\b|$)'.format(re.escape(section_name)))
    matches = pattern.findall(parsed_content)
    
    # Join the matched content to form the section content
    section_content = " ".join(matches).strip()
    
    return section_content




@app.route("/extract_and_store", methods=["POST"])
def extract_and_store():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"})

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Empty file name"})

    try:
        parsed_content = parse_document(file)
        predicted_section = predict_sections_ml(parsed_content)
        
        # Store parsed content Law and predicted section in MongoDB
        parsed_content_id = parsed_content_collection.insert_one({
            "content": parsed_content,
            "predicted_sections": predicted_section
        }).inserted_id
        
        return jsonify({"parsed_content_id": str(parsed_content_id)})
    except Exception as e:
        return jsonify({"error": str(e)})
users_collection = db['users']

# Route for user registration
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    firstname = data.get("firstname")
    lastname = data.get("lastname")
    email = data.get("email")
    password = data.get("password")

    # Check if user already exists
    if users_collection.find_one({"email": email}):
        return jsonify({"error": "Email already exists"}), 400

    # Insert new user into the database
    user_id = users_collection.insert_one({
        "firstname": firstname,
        "lastname": lastname,
        "email": email,
        "password": password
    }).inserted_id

    # Set session for the logged-in user
    session["user_id"] = str(user_id)

    return jsonify({"message": "User registered successfully"}), 200

# Route for user login
@app.route("/login")
def login_page():
    return render_template("login.html")

# Route for user login
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    # Check if user exists Law and password matches
    user = users_collection.find_one({"email": email, "password": password})
    if user:
        # Set session for the logged-in user
        session["user_id"] = str(user["_id"])
        return jsonify({"message": "Login successful"}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

# Route for rendering the index page
@app.route("/index")
def render_index():
    # Check if user is logged in
    if "user_id" in session:
        # Render the index page
        return render_template("index.html")
    else:
        # Redirect to the login page if user is not logged in
        return redirect(url_for("login_page"))
    
    
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import pandas as pd
import joblib

# Load labeled data
df = pd.read_csv('dataset/labeled_data.csv')

specified_sections = [
    'Payment terms',
    'Intellectual Property Rights',
    'Insurance Requirements',
    'Termination clause',
    'Governing Law and Jurisdiction'
]

df_filtered = df[df['section'].isin(specified_sections)]
# Clean 'text' column
df['clean_text'] = df['text'].apply(lambda x: re.sub(r'[^\w\s]', '', x).lower())

# Display DataFrame
print(df[['section', 'clean_text']])

# TF-IDF Vectorization
tfidf_vectorizer = TfidfVectorizer()
X = tfidf_vectorizer.fit_transform(df['clean_text'])
y = df['section']

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Choose Law and train model
clf = RandomForestClassifier()
clf.fit(X_train, y_train)

# Evaluate model
accuracy = clf.score(X_test, y_test)
print(f"Model Accuracy: {accuracy}")

# Save trained model
joblib.dump(clf, 'trained_model.pkl')


clf = joblib.load('trained_model.pkl')
def predict_sections_ml(parsed_content):
    # Preprocess Law and extract features from parsed content
    clean_content = re.sub(r'[^\w\s]', '', parsed_content).lower()
    features = tfidf_vectorizer.transform([clean_content])
    
    # Predict section
    predicted_section = clf.predict(features)[0]
    print(f"Predicted Section: {predicted_section}")  # Debugging print
    return [predicted_section]
def extract_section_content(parsed_content, section_name):
    # Define the start Law and end patterns for each section
    sections_patterns = {
        "Payment terms": r'Payment terms([\s\S]*?)(?=(?:[A-Z][A-Za-z0-9\s]+:|$))',
        "Intellectual Property Rights": r'Intellectual Property Rights([\s\S]*?)(?=(?:[A-Z][A-Za-z0-9\s]+:|$))',
        "Termination clause": r'Termination clause([\s\S]*?)(?=(?:[A-Z][A-Za-z0-9\s]+:|$))',
        "Governing Law and Jurisdiction": r'Governing Law and Jurisdiction([\s\S]*?)(?=(?:[A-Z][A-Za-z0-9\s]+:|$)|$)',
        "Insurance Requirements": r'Insurance Requirements([\s\S]*?)(?=(?:[A-Z][A-Za-z0-9\s]+:|$)|$)'
    }
    
    pattern = re.compile(sections_patterns.get(section_name, ""), re.IGNORECASE)
    matches = pattern.findall(parsed_content)
    
    # Join the matched content to form the section content
    section_content = " ".join(matches).strip()
    
    return section_content if section_content else ""




@app.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Empty file name"}), 400

    try:
        parsed_content = parse_document(file)
        
        # Predict sections using ML
        predicted_sections = predict_sections_ml(parsed_content)
        
        # Store parsed content Law and predicted sections in MongoDB
        parsed_content_id = parsed_content_collection.insert_one({
            "content": parsed_content,
            "predicted_sections": predicted_sections
        }).inserted_id

        return jsonify({"parsed_content_id": str(parsed_content_id)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/parse/<parsed_content_id>")
def parse(parsed_content_id):
    parsed_content_data = parsed_content_collection.find_one({"_id": ObjectId(parsed_content_id)})
    
    if parsed_content_data:
        parsed_content = parsed_content_data["content"]

        # Extract Law and display specific sections Law and their content
        extracted_sections = {}
        for section in specified_sections:
            section_content = extract_section_content(parsed_content, section)
            if section_content:  # Only add non-empty sections
                extracted_sections[section] = section_content

        return render_template("parse.html", extracted_sections=extracted_sections)
    else:
        return jsonify({"error": "Parsed content not found"}), 404


if __name__ == "__main__":
    app.run(debug=True)
