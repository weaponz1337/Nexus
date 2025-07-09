import sqlite3

conn = sqlite3.connect('data.db')  # Creates a new database file if it doesn’t exist
cursor = conn.cursor()

# Create the applications table
conn.execute('''CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT,
    role TEXT,
    location TEXT,
    status TEXT,
    applied_date TEXT,
    notes TEXT
)''')

conn.commit()
conn.close()
