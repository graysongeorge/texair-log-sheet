import os
import tempfile
from datetime import datetime
from functools import wraps

from flask import Flask, request, render_template, redirect, url_for, session
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename


app = Flask(__name__)

# -----------------------------
# App configuration
# -----------------------------

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

app.secret_key = os.getenv("SECRET_KEY", "default_key_if_not_set")

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_TIMEOUT"] = 20

mail = Mail(app)

LOGIN_USERNAME = os.getenv("LOGIN_USERNAME", "driver")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "driver")

RECIPIENT_EMAILS = os.getenv(
    "RECIPIENT_EMAIL",
    "notifications@texairdelivery.com"
).split(",")

PRIVACY_POLICY_URL = "https://graysongeorge.github.io/texair-log-sheet/"


# -----------------------------
# Helpers
# -----------------------------

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


# -----------------------------
# Routes
# -----------------------------

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
    app.logger.info("UPLOAD START")

    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    uploaded_file = request.files.get("file")

    if not first_name or not last_name:
        return "Missing first or last name.", 400

    if not uploaded_file:
        return "Missing file.", 400

    if not allowed_file(uploaded_file.filename):
        return "Bad file type. Please upload JPG, JPEG, PNG, or PDF.", 400

    original_filename = secure_filename(uploaded_file.filename)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            uploaded_file.save(temp_file.name)
            temp_path = temp_file.name

        app.logger.info("FILE SAVED TEMPORARILY")

        current_date = datetime.now().strftime("%m-%d-%Y")
        subject = f"Daily Activity Sheet - {first_name} {last_name} - {current_date}"

        msg = Message(
            subject=subject,
            sender=app.config["MAIL_USERNAME"],
            recipients=[email.strip() for email in RECIPIENT_EMAILS if email.strip()]
        )

        msg.body = (
            f"Daily activity sheet submitted by {first_name} {last_name}.\n\n"
            f"Submission Date: {current_date}"
        )

        app.logger.info("ATTACHING FILE")

        with open(temp_path, "rb") as file_data:
            msg.attach(
                original_filename,
                "application/octet-stream",
                file_data.read()
            )

        app.logger.info("SENDING EMAIL")
        mail.send(msg)
        app.logger.info("EMAIL SENT")

        return render_template("confirmation.html")

    except Exception as e:
        app.logger.error(f"UPLOAD FAILED: {e}")
        return f"Failed to send submission: {e}", 500

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
            app.logger.info("TEMP FILE DELETED")


if __name__ == "__main__":
    app.run(debug=False)