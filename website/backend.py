from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
import mysql.connector
from flask_cors import CORS
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key
CORS(app)  # Enable CORS for front-end to communicate with back-end

# Database connection
db = mysql.connector.connect(
    host="34.170.86.57",
    user="viewer",
    password="123",
    database="PapersDB"
)

# Serve the main HTML file
@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'frontend.html')

# Serve static files (JS and CSS)
@app.route('/<path:filename>')
def serve_static_files(filename):
    return send_from_directory('.', filename)

@app.route('/search', methods=['GET'])
def search_papers():
    if 'user_id' not in session:
        return jsonify({"error": "Authentication required"}), 401

    keywords = request.args.get('keywords')
    if not keywords:
        return jsonify({"error": "Need at least one keyword"}), 400

    keywords_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
    if len(keywords_list) < 1 or len(keywords_list) > 3:
        return jsonify({"error": "1-3 keywords allowed"}), 400

    while len(keywords_list) < 3:
        keywords_list.append(None)

    cursor = db.cursor(dictionary=True)
    try:
        cursor.callproc('search_papers', [keywords_list[0], keywords_list[1], keywords_list[2], session['user_id']])
        for result in cursor.stored_results():
            results = result.fetchall()

        paper_ids = [row['paper_id'] for row in results]

        liked_paper_ids = set()
        if paper_ids:
            format_strings = ','.join(['%s'] * len(paper_ids))
            cursor.execute(f"""
                SELECT paper_id FROM Likes WHERE user_id = %s AND paper_id IN ({format_strings})
            """, [session['user_id']] + paper_ids)
            liked_papers = cursor.fetchall()
            liked_paper_ids = {row['paper_id'] for row in liked_papers}

        for row in results:
            row['liked'] = row['paper_id'] in liked_paper_ids

        return jsonify(results)
    except mysql.connector.Error as err:
        return jsonify({"error": "Database query failed", "details": str(err)}), 500
    finally:
        cursor.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username_or_email = data.get('username_or_email')
    password = data.get('password')

    if not username_or_email or not password:
        return jsonify({"success": False, "error": "Username and password are required"}), 400

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT * FROM `User` WHERE username = %s OR email = %s
        """, (username_or_email, username_or_email))
        user = cursor.fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session.permanent = False
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "error": "Invalid credentials"}), 401
    except mysql.connector.Error as err:
        return jsonify({"success": False, "error": "Database query failed", "details": str(err)}), 500
    finally:
        cursor.close()

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('serve_static_files', filename='login.html'))

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({"success": False, "error": "All fields are required"}), 400

    if not email.endswith('@gmail.com'):
        return jsonify({"success": False, "error": "Email must be a Gmail address"}), 400

    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT * FROM User WHERE username = %s OR email = %s
        """, (username, email))
        if cursor.fetchone():
            return jsonify({"success": False, "error": "Username or email already exists"}), 409

        cursor.execute("""
            INSERT INTO User (username, email, password) VALUES (%s, %s, %s)
        """, (username, email, password))
        db.commit()
        return jsonify({"success": True}), 201
    except mysql.connector.Error as err:
        return jsonify({"success": False, "error": "Database error", "details": str(err)}), 500
    finally:
        cursor.close()

@app.route('/create-leaderboard', methods=['POST'])
def create_leaderboard():
    if 'user_id' not in session:
        return jsonify({"error": "Authentication required"}), 401

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO Leaderboards (ranking_date, time_period_days)
            VALUES (NOW(), %s)
        """, (1000,))
        db.commit()
        leaderboard_id = cursor.lastrowid

        cursor.callproc('GetAndInsertTopRankedPapers', [leaderboard_id])

        cursor.execute("""
            SELECT ai.paper_id, p.title, COUNT(l.user_id) AS num_likes, ai.ranking
            FROM AppearsIn ai
            LEFT JOIN Likes l ON ai.paper_id = l.paper_id
            JOIN Papers p ON ai.paper_id = p.paper_id
            WHERE ai.leaderboard_id = %s
            GROUP BY ai.paper_id, p.title, ai.ranking
            ORDER BY ai.ranking ASC
        """, (leaderboard_id,))
        top_papers = cursor.fetchall()

        return jsonify({"leaderboard_id": leaderboard_id, "top_papers": top_papers}), 200
    except mysql.connector.Error as err:
        return jsonify({"error": "Database operation failed", "details": str(err)}), 500
    finally:
        cursor.close()

@app.route('/recommend', methods=['GET'])
def recommend_papers():
    if 'user_id' not in session:
        return jsonify({"error": "Authentication required"}), 401

    cursor = db.cursor(dictionary=True)
    try:
        cursor.callproc('RecommendPapers', [session['user_id']])
        for result in cursor.stored_results():
            papers = result.fetchall()
        return jsonify(papers), 200 if papers else 404
    except mysql.connector.Error as err:
        return jsonify({"error": "Database query failed", "details": str(err)}), 500
    finally:
        cursor.close()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
