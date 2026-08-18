from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import pandas as pd
import joblib

app = Flask(__name__)

app.secret_key = "change_this_to_a_random_secret_key"

PROFILE_FILE = "student_details.xlsx"
MODEL_FILE = "attendance_forecasting_models.pkl"

profile_df = pd.read_excel(PROFILE_FILE)

profile_df["Roll_No"] = profile_df["Roll_No"].astype(str).str.strip()
profile_df["Name"] = profile_df["Name"].astype(str).str.strip()

models = joblib.load(MODEL_FILE)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


def get_db():

    connection = sqlite3.connect(
        "attendance_users.db"
    )

    connection.row_factory = sqlite3.Row

    return connection


def create_database():

    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


class User(UserMixin):

    def __init__(self, user_id, roll_no):

        self.id = user_id
        self.roll_no = roll_no


@login_manager.user_loader
def load_user(user_id):

    connection = get_db()

    user = connection.execute(
        """
        SELECT * FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    if user:

        return User(
            user["id"],
            user["roll_no"]
        )

    return None


def get_student(roll_no):

    student = profile_df[
        profile_df["Roll_No"] == roll_no
    ]

    if student.empty:

        return None

    return student.iloc[0]


@app.route("/")
@login_required
def home():

    student = get_student(
        current_user.roll_no
    )

    if student is None:

        logout_user()

        return redirect(
            url_for("login")
        )

    return render_template(
        "profile.html",
        student=student
    )


@app.route("/create-account", methods=["GET", "POST"])
def create_account():

    if request.method == "POST":

        roll_no = request.form.get(
            "roll_no",
            ""
        ).strip()

        name = request.form.get(
            "name",
            ""
        ).strip()

        dob = request.form.get(
            "dob",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        student = get_student(roll_no)

        if student is None:

            flash(
                "Roll number not found.",
                "error"
            )

            return redirect(
                url_for("create_account")
            )

        student_name = str(
            student["Name"]
        ).strip()

        student_dob = pd.to_datetime(
            student["DOB"]
        ).strftime("%Y-%m-%d")

        if name.lower() != student_name.lower():

            flash(
                "Name does not match our records.",
                "error"
            )

            return redirect(
                url_for("create_account")
            )

        if dob != student_dob:

            flash(
                "Date of birth does not match our records.",
                "error"
            )

            return redirect(
                url_for("create_account")
            )

        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters.",
                "error"
            )

            return redirect(
                url_for("create_account")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("create_account")
            )

        connection = get_db()

        existing_user = connection.execute(
            """
            SELECT id FROM users
            WHERE roll_no = ?
            """,
            (roll_no,)
        ).fetchone()

        if existing_user:

            connection.close()

            flash(
                "Account already exists. Use Forgot Password if needed.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        hashed_password = generate_password_hash(
            password
        )

        connection.execute(
            """
            INSERT INTO users
            (roll_no, password)
            VALUES (?, ?)
            """,
            (
                roll_no,
                hashed_password
            )
        )

        connection.commit()
        connection.close()

        flash(
            "Account created successfully. You can now login.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "create_account.html"
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        roll_no = request.form.get(
            "roll_no",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        connection = get_db()

        user = connection.execute(
            """
            SELECT * FROM users
            WHERE roll_no = ?
            """,
            (roll_no,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            user_object = User(
                user["id"],
                user["roll_no"]
            )

            login_user(user_object)

            return redirect(
                url_for("home")
            )

        flash(
            "Invalid Roll Number or Password.",
            "error"
        )

    return render_template(
        "login.html"
    )


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        roll_no = request.form.get(
            "roll_no",
            ""
        ).strip()

        name = request.form.get(
            "name",
            ""
        ).strip()

        dob = request.form.get(
            "dob",
            ""
        ).strip()

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        student = get_student(roll_no)

        if student is None:

            flash(
                "Student record not found.",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

        student_name = str(
            student["Name"]
        ).strip()

        student_dob = pd.to_datetime(
            student["DOB"]
        ).strftime("%Y-%m-%d")

        if name.lower() != student_name.lower():

            flash(
                "Name does not match our records.",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

        if dob != student_dob:

            flash(
                "Date of birth does not match our records.",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

        if len(new_password) < 8:

            flash(
                "Password must contain at least 8 characters.",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

        if new_password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

        hashed_password = generate_password_hash(
            new_password
        )

        connection = get_db()

        existing_user = connection.execute(
            """
            SELECT id FROM users
            WHERE roll_no = ?
            """,
            (roll_no,)
        ).fetchone()

        if existing_user:

            connection.execute(
                """
                UPDATE users
                SET password = ?
                WHERE roll_no = ?
                """,
                (
                    hashed_password,
                    roll_no
                )
            )

        else:

            connection.execute(
                """
                INSERT INTO users
                (roll_no, password)
                VALUES (?, ?)
                """,
                (
                    roll_no,
                    hashed_password
                )
            )

        connection.commit()
        connection.close()

        flash(
            "Password reset successfully. You can now login.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "forgot_password.html"
    )


@app.route("/prediction")
@login_required
def prediction():

    student = get_student(
        current_user.roll_no
    )

    if student is None:

        return redirect(
            url_for("logout")
        )

    return render_template(
        "prediction.html",
        student=student
    )


@app.route("/predict", methods=["POST"])
@login_required
def predict():

    student_id = current_user.roll_no

    if student_id not in models:

        return jsonify({
            "error": "Attendance forecasting model not found."
        }), 404

    student_model = models[
        student_id
    ]

    model = student_model["model"]

    history = student_model["history"]

    future = model.make_future_dataframe(
        periods=1,
        freq="MS"
    )

    forecast = model.predict(
        future
    )

    prediction = forecast.iloc[-1]["yhat"]

    prediction = max(
        0,
        min(100, prediction)
    )

    prediction = round(
        float(prediction),
        2
    )

    last_date = pd.to_datetime(
        history["ds"].iloc[-1]
    )

    next_month = (
        last_date +
        pd.offsets.MonthBegin(1)
    )

    if prediction <= 75:

        level = "Low"

    elif prediction <= 90:

        level = "Medium"

    else:

        level = "High"

    return jsonify({

        "roll_no": student_id,

        "student_name":
            student_model["student_name"],

        "predicted_month":
            next_month.strftime("%B %Y"),

        "predicted_attendance":
            prediction,

        "attendance_level":
            level
    })


@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(
        url_for("login")
    )


create_database()


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )