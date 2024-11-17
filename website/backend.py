from flask import Flask, request, jsonify, send_from_directory
import mysql.connector
from flask_cors import CORS

app = Flask(__name__)
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
    except mysql.connector.Error as err:
        return jsonify({"error": "Database query failed", "details": str(err)}), 500
    finally:
        cursor.close()

    return jsonify(results)




if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)


