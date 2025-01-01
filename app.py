import os
import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from datetime import datetime

app = Flask(__name__)

# Use the environment variable for the secret key
app.secret_key = os.getenv('SECRET_KEY', 'default_key_if_not_set')  # Replace 'default_key_if_not_set' with a safe fallback key

# Logging configuration
logging.basicConfig(level=logging.INFO)
app.logger.info("Application started")

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB limit
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Configuration for email
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'texairlogs@gmail.com'
app.config['MAIL_PASSWORD'] = 'nepz ocpl zjcs soij'
mail = Mail(app)

# Allowed credentials
ALLOWED_USERNAME = "driver"
ALLOWED_PASSWORD = "driver"

# Helper function to check file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def login():
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('submit'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def authenticate():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == ALLOWED_USERNAME and password == ALLOWED_PASSWORD:
        session['logged_in'] = True
        return redirect(url_for('submit'))
    else:
        return render_template('login.html', error="Invalid username or password.")

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/submit')
def submit():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))

    if 'file' not in request.files:
        return render_template('error.html', message="No file part provided."), 400

    file = request.files['file']
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')

    if not first_name or not last_name:
        return render_template('error.html', message="First and last name are required."), 400

    email = 'notifications@texairdelivery.com'

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # Generate current date for the email subject
            current_date = datetime.now().strftime("%m-%d-%Y")
            subject = f"Daily Activity Sheet - {current_date} - {first_name} {last_name}"

            # Send email
            msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f"Attached is the daily activity sheet submitted by {first_name} {last_name}."
            with app.open_resource(filepath) as fp:
                msg.attach(filename, "application/octet-stream", fp.read())
            mail.send(msg)

            app.logger.info(f"Email sent successfully to {email} by {first_name} {last_name}")
            return render_template('confirmation.html', email=email, name=f"{first_name} {last_name}")

        except Exception as e:
            app.logger.error(f"Error sending email: {e}")
            return render_template('error.html', message="Failed to send email. Please try again later."), 500

        finally:
            # Cleanup the uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)

    else:
        return render_template('error.html', message="Invalid file type or size exceeded."), 400

if __name__ == '__main__':
    app.run(debug=False)
