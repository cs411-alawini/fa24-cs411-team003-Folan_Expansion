def initialize_most_liked_papers_procedure():
    cursor = db.cursor()
    try:
        # Drop existing procedure if it exists
        cursor.execute("DROP PROCEDURE IF EXISTS GetMostLikedPapers")
        
        # Create new procedure
        cursor.execute("""
            CREATE PROCEDURE GetMostLikedPapers(IN user_id INT)
            BEGIN
                SELECT
                    p.paper_id,
                    p.title,
                    COUNT(l_all.user_id) AS total_likes
                FROM
                    Papers p
                JOIN
                    Likes l ON l.paper_id = p.paper_id
                JOIN
                    Likes l_all ON p.paper_id = l_all.paper_id
                WHERE
                    l.user_id = user_id
                    AND l.time_liked >= NOW() - INTERVAL 30 DAY
                GROUP BY
                    p.paper_id, p.title
                ORDER BY
                    total_likes DESC
                LIMIT 15;
            END
        """)
        
        print("Most liked papers procedure initialized successfully")
        
    except mysql.connector.Error as err:
        print(f"Error initializing most liked papers procedure: {err}")
        db.rollback()
    finally:
        cursor.close()