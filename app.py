import sqlite3
import os
from flask import Flask, render_template, redirect, request, flash
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Database configuration
DATABASE = 'data.db'

def init_db():
    """Initialize database if it doesn't exist"""
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        conn.execute('''CREATE TABLE applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            location TEXT,
            status TEXT DEFAULT 'Applied',
            applied_date TEXT,
            notes TEXT
        )''')
        conn.commit()
        conn.close()

# Initialize database on startup
init_db()

@app.route("/")
def _index():
    return render_template("home.html")

@app.route("/tools/")
def tools_index():
    
    return render_template("tools.html")
@app.route("/applications")
def applications_index():
    return render_template("index.html")

@app.route("/add", methods=["GET", "POST"])
@app.route("/add/", methods=["GET", "POST"])
def add_application():
    print("incoming request")
    if request.method == "POST":
        #grab form data
        company = request.form["company"]
        role = request.form["role"]
        location = request.form["location"]
        status = request.form["status"]
        applied_date = request.form["applied_date"]
        notes = request.form["notes"]


        # Validate required fields
        if not company or not role:
            return render_template("add.html", error="Company and Role are required fields")
        
        # Insert into DB
        try:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("INSERT INTO applications (company, role, location, status, applied_date, notes) VALUES (?,?,?,?,?,?)",
                     (company, role, location, status, applied_date, notes))
            conn.commit()
            conn.close()
            flash("Application added successfully!", "success")
            return redirect("/view")  # Redirect after successful submission
        except Exception as e:
            return render_template("add.html", error=f"Database error: {str(e)}")

    return render_template("add.html")

@app.route("/view")
def view_application():
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM applications ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()  # Fixed missing parentheses
        return render_template("view.html", applications=rows)
    except Exception as e:
        return render_template("view.html", applications=[], error=f"Database error: {str(e)}")

@app.route("/citation", methods=["GET", "POST"])
def citation():
    citation_text = ""
    if request.method == "POST":
        url = request.form["url"]
        try:
            page = requests.get(url, timeout=5)
            soup = BeautifulSoup(page.text, "html.parser")
            title = soup.title.string if soup.title else "No Title"
            domain = urlparse(url).netloc.replace("www.", "")
            citation_text = f"{title}. ({domain}). {url}"
        except Exception as e:
            citation_text = f"Error: {e}"

    return render_template("citation.html", citation=citation_text)

if __name__ == "__main__":
    app.run(debug=True)
