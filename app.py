import os
import cv2
import numpy as np
from PIL import Image
from fpdf import FPDF
from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB limit
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.secret_key = os.getenv('SECRET_KEY', 'default_key_if_not_set')
mail = Mail(app)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(PROCESSED_FOLDER):
    os.makedirs(PROCESSED_FOLDER)

# Allowed credentials
ALLOWED_USERNAME = os.getenv('LOGIN_USERNAME', 'default_username')
ALLOWED_PASSWORD = os.getenv('LOGIN_PASSWORD', 'default_password')

# Helper function to check file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to process image
def process_image(filepath):
    # Load the image
    image = cv2.imread(filepath)
    original = image.copy()

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply GaussianBlur and detect edges
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 75, 200)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    # Loop over contours to find a rectangle (document outline)
    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) == 4:
            doc_outline = approx
            break
    else:
        # If no rectangle is found, save the original image
        return filepath

    # Perform perspective transformation
    pts = doc_outline.reshape(4, 2)
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    # Compute the dimensions of the new image
    (tl, tr, br, bl) = rect
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(original, M, (maxWidth, maxHeight))

    # Save the processed image
    processed_path = os.path.join(app.config['PROCESSED_FOLDER'], "processed.png")
    cv2.imwrite(processed_path, warped)

    return processed_path

# Helper function to convert image to PDF
def convert_to_pdf(image_path):
    pdf_path = os.path.splitext(image_path)[0] + ".pdf"
    image = Image.open(image_path)
    image = image.convert('RGB')
    image.save(pdf_path)
    return pdf_path

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def login():
    if 'logged_in' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def authenticate():
    username = request.form.get('username')
    password = request.form.get('password')
    if username == ALLOWED_USERNAME and password == ALLOWED_PASSWORD:
        session['logged_in'] = True
        return redirect(url_for('index'))
    return render_template('login.html', error="Invalid username or password.")

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/index')
@login_required
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    file = request.files['file']

    if not first_name or not last_name or not file or not allowed_file(file.filename):
        return "Invalid submission. Please fill out all fields and upload a valid file."

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Process the image and convert to PDF
    processed_path = process_image(filepath)
    pdf_path = convert_to_pdf(processed_path)

    # Send email with attachment
    current_date = datetime.now().strftime("%m-%d-%Y")
    subject = f"Log Submission from {first_name} {last_name} - {current_date}"
    try:
        msg = Message(subject,
                      sender=app.config['MAIL_USERNAME'],
                      recipients=['notifications@texairdelivery.com'])
        msg.body = f"Log submitted by {first_name} {last_name}."
        with app.open_resource(pdf_path) as fp:
            msg.attach(os.path.basename(pdf_path), "application/pdf", fp.read())
        mail.send(msg)
        return render_template('confirmation.html')

    except Exception as e:
        return f"Failed to send email: {e}"

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
        if os.path.exists(processed_path):
            os.remove(processed_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

if __name__ == '__main__':
    app.run(debug=True)
