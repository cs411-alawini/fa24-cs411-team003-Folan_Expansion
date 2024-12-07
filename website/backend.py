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

# Leaderboard endpoint
# @app.route('/leaderboard', methods=['GET'])
# def leaderboard():
#     # Reconnect if the connection is not active
#     if not db.is_connected():
#         try:
#             db.reconnect()
#             print("Reconnected to the database.")
#         except mysql.connector.Error as err:
#             return jsonify({"error": "Unable to reconnect to the database", "details": str(err)}), 500

#     period = request.args.get('period')
#     cursor = db.cursor(dictionary=True)
#     if period == "day":
#         cursor.execute("""
#             SELECT Papers.title, AppearsIn.ranking
#             FROM Papers
#             JOIN AppearsIn ON Papers.paper_id = AppearsIn.paper_id
#             WHERE leaderboard_id IN (
#                 SELECT leaderboard_id FROM Leaderboards WHERE time_period_days = 1
#             )
#         """)
#     else:
#         cursor.execute("""
#             SELECT Papers.title, AppearsIn.ranking
#             FROM Papers
#             JOIN AppearsIn ON Papers.paper_id = AppearsIn.paper_id
#             WHERE leaderboard_id IN (
#                 SELECT leaderboard_id FROM Leaderboards WHERE time_period_days > 1
#             )
#         """)
#     results = cursor.fetchall()
#     cursor.close()
#     return jsonify(results)

# Search endpoint
@app.route('/search', methods=['GET'])
def search_papers():
    if 'user_id' not in session:
        return jsonify({"error": "Authentication required"}), 401

    keywords = request.args.get('keywords')
    if not keywords:
        return jsonify({"error": "Need at least one keyword"}), 400

    # Split keywords and clean up
    keywords_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
    if len(keywords_list) < 1:
        return jsonify({"error": "Need at least one keyword"}), 400
    if len(keywords_list) > 3:
        return jsonify({"error": "At most three keywords allowed"}), 400

    # Construct the dynamic SQL query
    keyword_conditions = []
    for kw in keywords_list:
        keyword_conditions.append(f"(p.title LIKE '%{kw}%' OR p.abstract LIKE '%{kw}%')")

    where_clause = " OR ".join(keyword_conditions)

    query = f"""
        WITH KeywordMatches AS (
            SELECT
                p.*,
                (
                    { " + ".join([f"CASE WHEN p.title LIKE '%{kw}%' THEN 2 ELSE 0 END + CASE WHEN p.abstract LIKE '%{kw}%' THEN 1 ELSE 0 END" for kw in keywords_list]) }
                ) AS relevance_score,
                (
                    { " + ".join([f"CASE WHEN p.title LIKE '%{kw}%' OR p.abstract LIKE '%{kw}%' THEN 1 ELSE 0 END" for kw in keywords_list]) }
                ) AS keywords_matched_count
            FROM
                Papers p
            WHERE
                {where_clause}
        )
        SELECT
            km.paper_id,  -- Include paper_id in the results
            km.title,
            km.abstract,
            km.citation_num,
            km.relevance_score,
            (0.7 * km.relevance_score) + (0.3 * km.citation_num) AS composite_score
        FROM
            KeywordMatches km
        ORDER BY
            (CASE WHEN km.keywords_matched_count = {len(keywords_list)} THEN 1 ELSE 0 END) DESC,
            composite_score DESC
        LIMIT 15;
    """

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(query)
        results = cursor.fetchall()

        # Get list of paper_ids from the results
        paper_ids = [row['paper_id'] for row in results]

        # Fetch liked papers for the user
        if paper_ids:
            format_strings = ','.join(['%s'] * len(paper_ids))
            cursor.execute(f"""
                SELECT paper_id FROM Likes WHERE user_id = %s AND paper_id IN ({format_strings})
            """, [session['user_id']] + paper_ids)
            liked_papers = cursor.fetchall()
            liked_paper_ids = set([row['paper_id'] for row in liked_papers])
        else:
            liked_paper_ids = set()

        # Add 'liked' flag to each result
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
        if user:
            stored_password = user['password']
            # If passwords are stored in plain text (not recommended)
            if stored_password == password:
                session['user_id'] = user['user_id']  # Store user ID in session
                return jsonify({"success": True}), 200
            else:
                return jsonify({"success": False, "error": "Invalid credentials"}), 401
        else:
            return jsonify({"success": False, "error": "User not found"}), 404
    except mysql.connector.Error as err:
        return jsonify({"success": False, "error": "Database query failed", "details": str(err)}), 500
    finally:
        cursor.close()

# Add a logout route
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

    # Validate that the email is a Gmail address
    if not email.endswith('@gmail.com'):
        return jsonify({"success": False, "error": "Email must be a Gmail address"}), 400

    cursor = db.cursor()
    try:
        # Check if username or email already exists
        cursor.execute("""
            SELECT * FROM User WHERE username = %s OR email = %s
        """, (username, email))
        if cursor.fetchone():
            return jsonify({"success": False, "error": "Username or email already exists"}), 409

        # Insert new user
        cursor.execute("""
            INSERT INTO User (username, email, password) VALUES (%s, %s, %s)
        """, (username, email, password))
        db.commit()

        return jsonify({"success": True}), 201

    except mysql.connector.Error as err:
        return jsonify({"success": False, "error": "Database error", "details": str(err)}), 500
    finally:
        cursor.close()

@app.route('/is_authenticated')
def is_authenticated():
    return jsonify({'authenticated': 'user_id' in session}), 200

@app.route('/like', methods=['POST'])
def like_paper():
    if 'user_id' not in session:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    paper_id = data.get('paper_id')

    if not paper_id:
        return jsonify({"error": "Paper ID is required"}), 400

    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO Likes (user_id, paper_id, time_liked)
            VALUES (%s, %s, NOW())
        """, (session['user_id'], paper_id))
        db.commit()
        return jsonify({"success": True}), 200
    except mysql.connector.Error as err:
        return jsonify({"error": "Database error", "details": str(err)}), 500
    finally:
        cursor.close()

@app.route('/unlike', methods=['POST'])
def unlike_paper():
    if 'user_id' not in session:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    paper_id = data.get('paper_id')

    if not paper_id:
        return jsonify({"error": "Paper ID is required"}), 400

    cursor = db.cursor()
    try:
        cursor.execute("""
            DELETE FROM Likes WHERE user_id = %s AND paper_id = %s
        """, (session['user_id'], paper_id))
        db.commit()
        return jsonify({"success": True}), 200
    except mysql.connector.Error as err:
        return jsonify({"error": "Database error", "details": str(err)}), 500
    finally:
        cursor.close()

@app.route('/liked-papers', methods=['GET'])
def get_liked_papers():
    if 'user_id' not in session:
        return jsonify({"error": "Authentication required"}), 401

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT p.paper_id, p.title, p.abstract, p.citation_num
            FROM Papers p
            JOIN Likes l ON p.paper_id = l.paper_id
            WHERE l.user_id = %s
            ORDER BY l.time_liked DESC
        """, (session['user_id'],))
        papers = cursor.fetchall()
        return jsonify(papers), 200
    except mysql.connector.Error as err:
        return jsonify({"error": "Database error", "details": str(err)}), 500
    finally:
        cursor.close()

@app.route('/top-papers-day', methods=['GET'])
def top_papers_day():
    cursor = db.cursor(dictionary=True)
    try:
        query = """
            SELECT
                p.paper_id,
                p.title,
                p.abstract,
                p.citation_num,
                COUNT(li.paper_id) AS like_count,
                ROW_NUMBER() OVER (ORDER BY COUNT(li.paper_id) DESC) AS ranking
            FROM
                Papers p
            JOIN Likes li ON p.paper_id = li.paper_id
            JOIN Leaderboards l ON l.leaderboard_id = 1
            WHERE
                li.time_liked BETWEEN DATE_SUB(l.ranking_date, INTERVAL l.time_period_days DAY) AND l.ranking_date
            GROUP BY
                p.paper_id, l.leaderboard_id
            ORDER BY
                like_count DESC
            LIMIT 10;
        """
        cursor.execute(query)
        results = cursor.fetchall()
        return jsonify(results), 200
    except mysql.connector.Error as err:
        return jsonify({"error": "Database error", "details": str(err)}), 500
    finally:
        cursor.close()

@app.route('/top-papers-all-time', methods=['GET'])
def top_papers_all_time():
    cursor = db.cursor(dictionary=True)
    try:
        query = """
            SELECT
                p.paper_id,
                p.title,
                p.abstract,
                p.citation_num,
                COUNT(li.paper_id) AS like_count,
                ROW_NUMBER() OVER (ORDER BY COUNT(li.paper_id) DESC) AS ranking
            FROM
                Papers p
            JOIN Likes li ON p.paper_id = li.paper_id
            GROUP BY
                p.paper_id
            ORDER BY
                like_count DESC
            LIMIT 10;
        """
        cursor.execute(query)
        results = cursor.fetchall()
        return jsonify(results), 200
    except mysql.connector.Error as err:
        return jsonify({"error": "Database error", "details": str(err)}), 500
    finally:
        cursor.close()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)


