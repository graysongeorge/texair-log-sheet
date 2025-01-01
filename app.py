import os
from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from datetime import datetime

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
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


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    file = request.files['file']

    if not first_name or not last_name or not file or not allowed_file(file.filename):
        return "Invalid submission. Please fill out all fields and upload a valid file."

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Send email with attachment
    current_date = datetime.now().strftime("%m-%d-%Y")
    subject = f"Log Submission from {first_name} {last_name} - {current_date}"
    try:
        msg = Message(subject,
                      sender=app.config['MAIL_USERNAME'],
                      recipients=['notifications@texairdelivery.com'])
        msg.body = f"Log submitted by {first_name} {last_name}."
        with app.open_resource(filepath) as fp:
            msg.attach(filename, "application/octet-stream", fp.read())
        mail.send(msg)
        return "Submission successful! Thank you."

    except Exception as e:
        return f"Failed to send email: {e}"

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


if __name__ == '__main__':
    app.run(debug=True)
