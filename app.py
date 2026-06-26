import os
from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from datetime import datetime
from functools import wraps

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_TIMEOUT'] = 20
app.secret_key = os.getenv('SECRET_KEY', 'default_key_if_not_set')

mail = Mail(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_USERNAME = os.getenv('LOGIN_USERNAME', 'driver')
ALLOWED_PASSWORD = os.getenv('LOGIN_PASSWORD', 'driver')

RECIPIENT_EMAILS = os.getenv(
    'RECIPIENT_EMAIL',
    'notifications@texairdelivery.com'
).split(',')

PRIVACY_POLICY_URL = "https://graysongeorge.github.io/texair-log-sheet/"

def allowed_file(filename):
    return (
        filename
        and '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def login():
    if session.get('logged_in'):
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
    session.clear()
    return redirect(url_for('login'))

@app.route('/index')
@login_required
def index():
    return render_template('index.html')

@app.route('/privacy-policy')
def privacy_policy():
    return redirect(PRIVACY_POLICY_URL)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    app.logger.info("STEP 1")

    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    file = request.files.get('file')

    app.logger.info("STEP 2")

    if not first_name or not last_name:
        return "Missing name"

    if not file:
        return "Missing file"

    if not allowed_file(file.filename):
        return "Bad file type"

    app.logger.info("STEP 3")

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    file.save(filepath)

    app.logger.info("STEP 4")

    if os.path.exists(filepath):
        app.logger.info("FILE SAVED SUCCESSFULLY")
        os.remove(filepath)

    app.logger.info("STEP 5")

    return render_template("confirmation.html")

    try:
        msg = Message(
            subject,
            sender=app.config['MAIL_USERNAME'],
            recipients=RECIPIENT_EMAILS
        )
        msg.body = f"Log submitted by {first_name} {last_name}."

        with open(filepath, "rb") as fp:
            msg.attach(filename, "application/octet-stream", fp.read())

        mail.send(msg)

        return render_template('confirmation.html')

    except Exception as e:
        app.logger.error(f"Upload/email failed: {e}")
        return f"Failed to send email: {e}", 500

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    app.run(debug=False)