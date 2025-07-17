import sqlite3
import os
from flask import Flask, render_template, redirect, request, flash, jsonify
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import requests
import pid_tune

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

def validate_pid_parameters(kp, ki, kd):
    """Validate PID parameters are within realistic bounds"""
    errors = []
    
    # Realistic bounds for industrial PID controllers
    if not (0.01 <= kp <= 100):
        errors.append("Kp must be between 0.01 and 100")
    if not (0.001 <= ki <= 10):
        errors.append("Ki must be between 0.001 and 10")
    if not (0.0 <= kd <= 5):
        errors.append("Kd must be between 0.0 and 5")
    
    return errors

@app.route("/pid", methods=["GET", "POST"])
def pid():
    if request.method == "POST":
        try:
            # Extract parameters from form
            kp = float(request.form.get("kp", 0))
            ki = float(request.form.get("ki", 0))
            kd = float(request.form.get("kd", 0))
            
            # Validate parameters
            validation_errors = validate_pid_parameters(kp, ki, kd)
            if validation_errors:
                return render_template("pid.html", error="; ".join(validation_errors))
            
            # Extract optional system parameters
            kwargs = {}
            for param in ['process_gain', 'dead_time', 'time_constant', 'setpoint']:
                value = request.form.get(param)
                if value:
                    kwargs[param] = float(value)
            
            # Delegate all PID logic to pid_tune module
            results = pid_tune.process_pid_tuning(kp, ki, kd, **kwargs)
            
            return render_template("pid.html", results=results, success=True)
            
        except ValueError as e:
            return render_template("pid.html", error="Please enter valid numeric values for PID parameters")
        except Exception as e:
            return render_template("pid.html", error=f"PID tuning error: {str(e)}")
    
    return render_template("pid.html")

@app.route("/pid/optimize", methods=["GET", "POST"])
def pid_optimize():
    """Auto-tune PID parameters using optimization"""
    if request.method == "POST":
        try:
            # Get target performance criteria
            max_settling_time = float(request.form.get("max_settling_time", 10.0))
            max_overshoot = float(request.form.get("max_overshoot", 5.0))
            max_steady_error = float(request.form.get("max_steady_error", 1.0))
            
            # Custom bounds if provided
            kp_min = float(request.form.get("kp_min", 0.1))
            kp_max = float(request.form.get("kp_max", 10.0))
            ki_min = float(request.form.get("ki_min", 0.01))
            ki_max = float(request.form.get("ki_max", 2.0))
            kd_min = float(request.form.get("kd_min", 0.001))
            kd_max = float(request.form.get("kd_max", 1.0))
            
            bounds = [(kp_min, kp_max), (ki_min, ki_max), (kd_min, kd_max)]
            
            target_params = {
                'max_settling_time': max_settling_time,
                'max_overshoot': max_overshoot,
                'max_steady_error': max_steady_error
            }
            
            # Run optimization
            optimization_results = pid_tune.optimize_pid_parameters(target_params, bounds)
            
            return render_template("pid_optimize.html", 
                                 optimization_results=optimization_results, 
                                 success=True)
            
        except ValueError as e:
            return render_template("pid_optimize.html", error="Please enter valid numeric values")
        except Exception as e:
            return render_template("pid_optimize.html", error=f"Optimization error: {str(e)}")
    
    return render_template("pid_optimize.html")

@app.route("/pid/chart/<chart_type>")
def pid_chart(chart_type):
    """Generate chart images for PID simulation results"""
    try:
        # Get parameters from query string
        kp = float(request.args.get("kp", 1.0))
        ki = float(request.args.get("ki", 0.1))
        kd = float(request.args.get("kd", 0.05))
        
        # Validate parameters
        validation_errors = validate_pid_parameters(kp, ki, kd)
        if validation_errors:
            return jsonify({"error": "; ".join(validation_errors)}), 400
        
        # Generate chart using pid_tune module
        chart_data = pid_tune.generate_chart(kp, ki, kd, chart_type)
        
        return jsonify({"success": True, "chart_data": chart_data})
        
    except ValueError as e:
        return jsonify({"error": "Invalid parameters"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/pid/api", methods=["POST"])
def pid_api():
    """API endpoint for PID tuning - returns JSON"""
    try:
        data = request.get_json()
        kp = float(data.get("kp", 0))
        ki = float(data.get("ki", 0))
        kd = float(data.get("kd", 0))
        
        # Validate parameters
        validation_errors = validate_pid_parameters(kp, ki, kd)
        if validation_errors:
            return jsonify({"success": False, "error": "; ".join(validation_errors)}), 400
        
        # All logic handled in pid_tune module
        results = pid_tune.process_pid_tuning(kp, ki, kd)
        
        return jsonify({"success": True, "results": results})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

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
