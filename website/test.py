import mysql.connector

try:
    db = mysql.connector.connect(
        host="34.170.86.57",
        user="viewer",
        password="123",
        database="PapersDB",
        connection_timeout=5  # Timeout after 10 seconds
    )
    print("Connected to the database successfully!")
except mysql.connector.Error as err:
    print(f"Database connection error: {err}")
