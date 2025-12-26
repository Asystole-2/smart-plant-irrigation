import os
from flask import Flask, render_template, redirect, request, session, flash, url_for
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import google.generativeai as genai
from Interface.src.ai_analyzer import PlantCareAIAnalyzer

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# Database Configuration
app.config.update(
    MYSQL_HOST=os.getenv("MYSQL_HOST"),
    MYSQL_USER=os.getenv("MYSQL_USER"),
    MYSQL_PASSWORD=os.getenv("MYSQL_PASSWORD", ""),
    MYSQL_DB='SmartIrrigation',
    MYSQL_CURSORCLASS="DictCursor"
)
mysql = MySQL(app)

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("WARNING: GEMINI_API_KEY not found in .env file!")

genai.configure(api_key=api_key)
ai_model = genai.GenerativeModel('gemini-pro')

# Helper for login protection
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").lower()
        email = request.form.get("email").lower()
        password = request.form.get("password")

        hashed_pw = generate_password_hash(password)
        cur = mysql.connection.cursor()
        try:
            cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                        (username, email, hashed_pw))
            mysql.connection.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash("Username or Email already exists.", "error")
        finally:
            cur.close()
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = (request.form.get("identifier") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not identifier or not password:
            flash("Please enter both username/email and password.", "error")
            return render_template("login.html")

        ident_lc = identifier.lower()
        cur = mysql.connection.cursor()

        try:
            # Check if identifier is email or username
            if "@" in ident_lc:
                cur.execute("SELECT id, username, email, password, role FROM users WHERE LOWER(email)=%s LIMIT 1",
                            (ident_lc,))
            else:
                cur.execute("SELECT id, username, email, password, role FROM users WHERE LOWER(username)=%s LIMIT 1",
                            (ident_lc,))

            row = cur.fetchone()
            cur.close()

            if not row or not check_password_hash(row["password"], password):
                flash("Incorrect username/email or password.", "error")
                return render_template("login.html")

            # Set session variables
            session["user_id"] = row["id"]
            session["username"] = row["username"]
            session["role"] = row["role"]

            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))

        except Exception as e:
            flash("An error occurred during login.", "error")
            return render_template("login.html")

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session.get("user_id")
    cur = mysql.connection.cursor()

    # Fetch plants associated with user
    cur.execute("""
                SELECT p.*, MAX(m.moisture_level) as last_moisture, MAX(m.recorded_at) as last_update
                FROM plants p
                         LEFT JOIN moisture_readings m ON p.id = m.plant_id
                WHERE p.user_id = %s
                GROUP BY p.id
                """, (user_id,))
    user_plants = cur.fetchall()
    cur.close()

    return render_template("dashboard.html", plants=user_plants)


@app.route("/plant/<int:plant_id>")
@login_required
def plant_detail(plant_id):
    cur = mysql.connection.cursor()
    # Fetch plant details
    cur.execute("SELECT * FROM plants WHERE id = %s AND user_id = %s", (plant_id, session['user_id']))
    plant = cur.fetchone()

    if not plant:
        flash("Plant not found.", "error")
        return redirect(url_for('dashboard'))

    # Fetch latest moisture reading
    cur.execute("""
                SELECT moisture_level, recorded_at
                FROM moisture_readings
                WHERE plant_id = %s
                ORDER BY recorded_at DESC LIMIT 1
                """, (plant_id,))
    last_reading = cur.fetchone()

    cur.close()
    return render_template("plant_detail.html", plant=plant, last_reading=last_reading)


# Initialize analyzer globally
analyzer = PlantCareAIAnalyzer()

@app.route("/api/ai-tips/<int:plant_id>")
@login_required
def get_ai_tips(plant_id):
    cur = mysql.connection.cursor()
    # Fetch plant data and join with latest moisture reading
    cur.execute("""
                SELECT p.*, m.moisture_level as last_moisture
                FROM plants p
                         LEFT JOIN moisture_readings m ON p.id = m.plant_id
                WHERE p.id = %s
                  AND p.user_id = %s
                ORDER BY m.recorded_at DESC LIMIT 1
                """, (plant_id, session['user_id']))

    plant_data = cur.fetchone()
    cur.close()

    if not plant_data:
        return {"error": "Plant not found"}, 404

    # The analyzer now handles both success and failure cases safely
    advice = analyzer.get_care_advice(plant_data)
    return advice

@app.route("/update-plant-photo/<int:plant_id>", methods=["POST"])
def update_photo(plant_id):
    if 'photo' not in request.files: return redirect(url_for('dashboard'))
    file = request.files['photo']
    filename = f"plant_{plant_id}.jpg"
    file.save(os.path.join('static/uploads', filename))

    cur = mysql.connection.cursor()
    cur.execute("UPDATE plants SET image_url = %s WHERE id = %s", (filename, plant_id))
    mysql.connection.commit()
    return redirect(url_for('dashboard'))

@app.route("/notifications")
@login_required
def notifications():
    user_id = session.get("user_id")
    cur = mysql.connection.cursor()

    # Fetch notifications for the logged-in user
    cur.execute("""
                SELECT *
                FROM user_notifications
                WHERE user_id = %s
                ORDER BY created_at DESC LIMIT 50
                """, (user_id,))

    user_notifications = cur.fetchall()
    cur.close()

    return render_template(
        "notifications.html",
        active_page="notifications",
        notifications=user_notifications
    )


@app.route("/settings")
@login_required
def settings():
    user_id = session.get("user_id")
    users_list = []
    user_profile = {}

    cur = mysql.connection.cursor()
    try:
        # Get current user's profile data
        cur.execute("""
                    SELECT username, email, first_name, last_name, bio, profile_picture
                    FROM users
                    WHERE id = %s
                    """, (user_id,))
        user_data = cur.fetchone()

        if user_data:
            user_profile = user_data

        # If admin, fetch all users for the management table
        if session.get("role") == "admin":
            cur.execute("SELECT id, username, email, role FROM users ORDER BY id ASC")
            users_list = cur.fetchall()

    except Exception as e:
        flash("Error loading settings.", "error")
    finally:
        cur.close()

    return render_template(
        "settings.html",
        users=users_list,
        user_profile=user_profile,
        active_page="settings"
    )
@app.route("/logout")
def logout():
    # Clear all data from the session
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=True)