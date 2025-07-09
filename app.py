import sqlite3
from flask import Flask, render_template, redirect, request
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import requests

app = Flask(__name__)

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


        # Insert into DB
        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        c.execute( "INSERT INTO applications (company, role, location, status, applied_date, notes) VALUES (?,?,?,?,?,?)"
        (company, role, location, status, applied_date, notes)            
        )
        conn.commit()
        conn.close()



    return render_template("add.html")

@app.route("/view")
def view_application():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT * FROM applications")
    rows = c.fetchall()
    conn.close
    return render_template("view.html", applications=rows)

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
