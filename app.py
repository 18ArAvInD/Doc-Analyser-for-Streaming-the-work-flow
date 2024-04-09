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

'''
def parse_image(file):
    text_content = pytesseract.image_to_string(Image.open(io.BytesIO(file.read())))
    return text_content '''

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

def extract_sections(content):
    sections = {}
    
    # Extract sections if available
    payment_terms_match = re.search(r'Payment\s*Terms:(.*?)(?:Intellectual\s*Property\s*Rights:|Confidentiality\s*and\s*Non-Disclosure:|Termination\s*Clause:|Governing\s*Law\s*and\s*Jurisdiction:|$)', content, re.DOTALL | re.IGNORECASE)
    if payment_terms_match:
        sections['Payment Terms'] = payment_terms_match.group(1).strip()

    ip_rights_match = re.search(r'Intellectual\s*Property\s*Rights:(.*?)(?:Confidentiality\s*and\s*Non-Disclosure:|Termination\s*Clause:|Governing\s*Law\s*and\s*Jurisdiction:|$)', content, re.DOTALL | re.IGNORECASE)
    if ip_rights_match:
        sections['Intellectual Property Rights'] = ip_rights_match.group(1).strip()

    confidentiality_match = re.search(r'Confidentiality\s*and\s*Non-Disclosure:(.*?)(?:Termination\s*Clause:|Governing\s*Law\s*and\s*Jurisdiction:|$)', content, re.DOTALL | re.IGNORECASE)
    if confidentiality_match:
        sections['Confidentiality and Non-Disclosure'] = confidentiality_match.group(1).strip()

    termination_clause_match = re.search(r'Termination\s*Clause:(.*?)(?:Governing\s*Law\s*and\s*Jurisdiction:|$)', content, re.DOTALL | re.IGNORECASE)
    if termination_clause_match:
        sections['Termination Clause'] = termination_clause_match.group(1).strip()

    governing_law_match = re.search(r'Governing\s*Law\s*and\s*Jurisdiction:(.*?)$', content, re.DOTALL | re.IGNORECASE)
    if governing_law_match:
        sections['Governing Law and Jurisdiction'] = governing_law_match.group(1).strip()

    # If sections are not found, extract information directly from text
    if not sections:
        extracted_info = {}
        # Extract total amount
        total_amount_match = re.search(r'Total\s*Amount:\s*\$?(\d+(?:\.\d+)?)', content, re.IGNORECASE)
        if total_amount_match:
            extracted_info['total_amount'] = float(total_amount_match.group(1))

        # Extract date
        date_match = re.search(r'Date:\s*(\d{2}/\d{2}/\d{4})', content)
        if date_match:
            extracted_info['date'] = date_match.group(1)

        # Extract vendor name
        vendor_match = re.search(r'Vendor:\s*(.*)', content)
        if vendor_match:
            extracted_info['vendor'] = vendor_match.group(1)

        # Extract itemized list of purchases
        itemized_purchases = []
        item_pattern = r'(\d+)\s+(.+?)\s+\$?(\d+(?:\.\d+)?)'
        for match in re.finditer(item_pattern, content):
            quantity = int(match.group(1))
            item_name = match.group(2)
            price = float(match.group(3))
            itemized_purchases.append({'quantity': quantity, 'item_name': item_name, 'price': price})
        if itemized_purchases:
            extracted_info['itemized_purchases'] = itemized_purchases

        # Extract tax amount
        tax_match = re.search(r'Tax:\s*\$?(\d+(?:\.\d+)?)', content)
        if tax_match:
            extracted_info['tax_amount'] = float(tax_match.group(1))

        # Extract payment method
        payment_method_match = re.search(r'Payment\s*Method:\s*(.*)', content)
        if payment_method_match:
            extracted_info['payment_method'] = payment_method_match.group(1)

        return extracted_info

    return sections

'''
# Text processing functions
def tokenize_text(text):
    tokens = nltk.word_tokenize(text)
    return [token.lower() for token in tokens if token.isalnum()]

def get_sentiment(text):
    blob = TextBlob(text)
    return blob.sentiment.polarity '''

@app.route("/")
def index():
    return render_template("sma.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"})

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Empty file name"})

    try:
        parsed_content = parse_document(file)
        
        # Extract sections
        sections = extract_sections(parsed_content)
        
        # Store parsed content in MongoDB
        parsed_content_id = parsed_content_collection.insert_one({
            "content": parsed_content,
            "sections": sections
        }).inserted_id

        return jsonify({"parsed_content_id": str(parsed_content_id)})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/parse/<parsed_content_id>")
def parse(parsed_content_id):
    parsed_content = parsed_content_collection.find_one({"_id": ObjectId(parsed_content_id)})
    if parsed_content:
        return render_template("parse.html", parsed_content=parsed_content)
    else:
        return jsonify({"error": "Parsed content not found"})

@app.route("/extract_and_store", methods=["POST"])
def extract_and_store():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"})

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Empty file name"})

    try:
        parsed_content = parse_document(file)
        
        # Extract sections
        sections = extract_sections(parsed_content)
        
        # Store parsed content in MongoDB
        parsed_content_id = parsed_content_collection.insert_one(sections).inserted_id
        
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

    # Check if user exists and password matches
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
if __name__ == "__main__":
    app.run(debug=True)
