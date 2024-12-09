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

@app.route('/search', methods=['GET'])
def search_papers():
    if 'user_id' not in session:
        return jsonify({"error": "Authentication required"}), 401

    keywords = request.args.get('keywords')
    if not keywords:
        return jsonify({"error": "Need at least one keyword"}), 400

    keywords_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
    if len(keywords_list) < 1:
        return jsonify({"error": "Need at least one keyword"}), 400
    if len(keywords_list) > 3:
        return jsonify({"error": "At most three keywords allowed"}), 400

    cursor = db.cursor(dictionary=True)
    try:
        # Set transaction isolation level
        cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        cursor.execute("START TRANSACTION")

        # First advanced query - Search with scoring
        search_query = f"""
            WITH KeywordMatches AS (
                SELECT 
                    p.*,
                    (
                        { " + ".join([f"CASE WHEN p.title LIKE '%{kw}%' THEN 2 ELSE 0 END + CASE WHEN p.abstract LIKE '%{kw}%' THEN 1 ELSE 0 END" for kw in keywords_list]) }
                    ) AS relevance_score,
                    (
                        { " + ".join([f"CASE WHEN p.title LIKE '%{kw}%' OR p.abstract LIKE '%{kw}%' THEN 1 ELSE 0 END" for kw in keywords_list]) }
                    ) AS keywords_matched_count
                FROM Papers p
                WHERE { " OR ".join([f"(p.title LIKE '%{kw}%' OR p.abstract LIKE '%{kw}%')" for kw in keywords_list]) }
            )
            SELECT 
                km.*,
                (0.7 * km.relevance_score) + (0.3 * km.citation_num) AS composite_score
            FROM KeywordMatches km
            ORDER BY
                keywords_matched_count DESC,
                composite_score DESC
            LIMIT 15
        """
        cursor.execute(search_query)
        results = cursor.fetchall()
        
        # Second advanced query - Get user interaction stats with papers
        if results:
            paper_ids = [str(row['paper_id']) for row in results]
            stats_query = f"""
                SELECT 
                    p.paper_id,
                    COUNT(DISTINCT l.user_id) as like_count,
                    AVG(CASE WHEN l.user_id IS NOT NULL THEN 1 ELSE 0 END) as engagement_rate,
                    EXISTS(SELECT 1 FROM Likes WHERE user_id = %s AND paper_id = p.paper_id) as user_liked
                FROM Papers p
                LEFT JOIN Likes l ON p.paper_id = l.paper_id
                WHERE p.paper_id IN ({','.join(paper_ids)})
                GROUP BY p.paper_id
            """
            cursor.execute(stats_query, (session['user_id'],))
            paper_stats = {row['paper_id']: row for row in cursor.fetchall()}
            
            # Merge results
            for paper in results:
                stats = paper_stats.get(paper['paper_id'], {})
                paper.update({
                    'like_count': stats.get('like_count', 0),
                    'engagement_rate': float(stats.get('engagement_rate', 0)),
                    'liked': stats.get('user_liked', False)
                })

        cursor.execute("COMMIT")
        return jsonify(results)

    except mysql.connector.Error as err:
        cursor.execute("ROLLBACK")
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
                session.permanent = False  # Make session non-permanent
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
    if 'user_id' in session:
        cursor = db.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT username, email FROM User WHERE user_id = %s
            """, (session['user_id'],))
            user = cursor.fetchone()
            if user:
                return jsonify({
                    'authenticated': True,
                    'username': user['username'],
                    'email': user['email']
                }), 200
            else:
                return jsonify({'authenticated': False}), 200
        except mysql.connector.Error:
            return jsonify({'authenticated': False}), 200
        finally:
            cursor.close()
    else:
        return jsonify({'authenticated': False}), 200

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

# Remove the following routes related to top papers

# @app.route('/top-papers-day', methods=['GET'])
# def top_papers_day():
#     cursor = db.cursor(dictionary=True)
#     try:
#         cursor.execute("""
#             SELECT p.paper_id, p.title, p.abstract, p.citation_num, 
#                    (0.7 * p.relevance_score + 0.3 * p.citation_num) AS composite_score
#             FROM Papers p
#             JOIN Leaderboards l ON p.paper_id = l.paper_id
#             WHERE l.time_period_days = 1
#             ORDER BY composite_score DESC
#             LIMIT 10;
#         """)
#         papers = cursor.fetchall()
#         return jsonify(papers), 200
#     except mysql.connector.Error as err:
#         return jsonify({"error": "Database error", "details": str(err)}), 500
#     finally:
#         cursor.close()

# @app.route('/top-papers-all-time', methods=['GET'])
# def top_papers_all_time():
#     cursor = db.cursor(dictionary=True)
#     try:
#         cursor.execute("""
#             SELECT p.paper_id, p.title, p.abstract, p.citation_num, 
#                    (0.7 * p.relevance_score + 0.3 * p.citation_num) AS composite_score
#             FROM Papers p
#             JOIN Leaderboards l ON p.paper_id = l.paper_id
#             WHERE l.time_period_days > 1
#             ORDER BY composite_score DESC
#             LIMIT 10;
#         """)
#         papers = cursor.fetchall()
#         return jsonify(papers), 200
#     except mysql.connector.Error as err:
#         return jsonify({"error": "Database error", "details": str(err)}), 500
#     finally:
#         cursor.close()

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

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)




# TSET