import os
import base64
from datetime import datetime
from functools import wraps

from flask import Flask, request, render_template, redirect, url_for, session
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from werkzeug.utils import secure_filename

app = Flask(__name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

app.secret_key = os.getenv("SECRET_KEY", "default_key_if_not_set")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

LOGIN_USERNAME = os.getenv("LOGIN_USERNAME", "driver")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "driver")

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "texairlogs@gmail.com")

RECIPIENT_EMAILS = os.getenv(
    "RECIPIENT_EMAIL",
    "notifications@texairdelivery.com"
).split(",")

PRIVACY_POLICY_URL = "https://graysongeorge.github.io/texair-log-sheet/"


def allowed_file(filename):
    return (
        filename
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return route_function(*args, **kwargs)
    return wrapper


@app.route("/")
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def authenticate():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if username == LOGIN_USERNAME and password == LOGIN_PASSWORD:
        session["logged_in"] = True
        return redirect(url_for("index"))

    return render_template("login.html", error="Invalid username or password.")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/index")
@login_required
def index():
    return render_template("index.html")


@app.route("/privacy-policy")
def privacy_policy():
    return redirect(PRIVACY_POLICY_URL)


@app.route("/upload", methods=["POST"])
@login_required
def upload_file():
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    uploaded_file = request.files.get("file")

    if not first_name or not last_name:
        return "Missing first or last name.", 400

    if not uploaded_file:
        return "Missing file.", 400

    if not allowed_file(uploaded_file.filename):
        return "Bad file type. Please upload JPG, JPEG, PNG, or PDF.", 400

    if not SENDGRID_API_KEY:
        return "SendGrid API key is missing.", 500

    filename = secure_filename(uploaded_file.filename)
    file_bytes = uploaded_file.read()
    encoded_file = base64.b64encode(file_bytes).decode()

    current_date = datetime.now().strftime("%m-%d-%Y")
    subject = f"Daily Activity Sheet - {first_name} {last_name} - {current_date}"

    try:
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=[email.strip() for email in RECIPIENT_EMAILS if email.strip()],
            subject=subject,
            plain_text_content=(
                f"Daily activity sheet submitted by {first_name} {last_name}.\n\n"
                f"Submission Date: {current_date}"
            )
        )

        attachment = Attachment(
            FileContent(encoded_file),
            FileName(filename),
            FileType("application/octet-stream"),
            Disposition("attachment")
        )

        message.attachment = attachment

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        app.logger.info(f"SendGrid status code: {response.status_code}")

        return render_template("confirmation.html")

    except Exception as e:
        app.logger.error(f"SendGrid failed: {e}")
        return f"Failed to send submission: {e}", 500


if __name__ == "__main__":
    app.run(debug=False)