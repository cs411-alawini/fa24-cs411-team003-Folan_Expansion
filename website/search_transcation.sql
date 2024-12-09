
DELIMITER $$

CREATE PROCEDURE search_papers(
    IN keyword1 VARCHAR(255),
    IN keyword2 VARCHAR(255),
    IN keyword3 VARCHAR(255),
    IN user_id INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    
    WITH KeywordMatches AS (
        SELECT 
            p.*,
            (
                CASE WHEN p.title LIKE CONCAT('%', keyword1, '%') THEN 2 ELSE 0 END +
                CASE WHEN p.abstract LIKE CONCAT('%', keyword1, '%') THEN 1 ELSE 0 END +
                CASE WHEN keyword2 IS NOT NULL THEN 
                    CASE WHEN p.title LIKE CONCAT('%', keyword2, '%') THEN 2 ELSE 0 END +
                    CASE WHEN p.abstract LIKE CONCAT('%', keyword2, '%') THEN 1 ELSE 0 END
                ELSE 0 END +
                CASE WHEN keyword3 IS NOT NULL THEN 
                    CASE WHEN p.title LIKE CONCAT('%', keyword3, '%') THEN 2 ELSE 0 END +
                    CASE WHEN p.abstract LIKE CONCAT('%', keyword3, '%') THEN 1 ELSE 0 END
                ELSE 0 END
            ) AS relevance_score,
            (
                CASE WHEN p.title LIKE CONCAT('%', keyword1, '%') OR p.abstract LIKE CONCAT('%', keyword1, '%') THEN 1 ELSE 0 END +
                CASE WHEN keyword2 IS NOT NULL THEN 
                    CASE WHEN p.title LIKE CONCAT('%', keyword2, '%') OR p.abstract LIKE CONCAT('%', keyword2, '%') THEN 1 ELSE 0 END
                ELSE 0 END +
                CASE WHEN keyword3 IS NOT NULL THEN 
                    CASE WHEN p.title LIKE CONCAT('%', keyword3, '%') OR p.abstract LIKE CONCAT('%', keyword3, '%') THEN 1 ELSE 0 END
                ELSE 0 END
            ) AS keywords_matched_count
        FROM Papers p
        WHERE 
            p.title LIKE CONCAT('%', keyword1, '%') OR p.abstract LIKE CONCAT('%', keyword1, '%')
            OR (keyword2 IS NOT NULL AND (p.title LIKE CONCAT('%', keyword2, '%') OR p.abstract LIKE CONCAT('%', keyword2, '%')))
            OR (keyword3 IS NOT NULL AND (p.title LIKE CONCAT('%', keyword3, '%') OR p.abstract LIKE CONCAT('%', keyword3, '%')))
    )
    SELECT 
        km.*,
        COALESCE(l.like_count, 0) as like_count,
        COALESCE(l.engagement_rate, 0) as engagement_rate,
        COALESCE(l.user_liked, FALSE) as liked,
        (0.7 * km.relevance_score) + (0.3 * km.citation_num) AS composite_score
    FROM KeywordMatches km
    LEFT JOIN (
        SELECT 
            p.paper_id,
            COUNT(DISTINCT l.user_id) as like_count,
            AVG(CASE WHEN l.user_id IS NOT NULL THEN 1 ELSE 0 END) as engagement_rate,
            EXISTS(SELECT 1 FROM Likes WHERE user_id = user_id AND paper_id = p.paper_id) as user_liked
        FROM Papers p
        LEFT JOIN Likes l ON p.paper_id = l.paper_id
        GROUP BY p.paper_id
    ) l ON km.paper_id = l.paper_id
    ORDER BY
        km.keywords_matched_count DESC,
        composite_score DESC
    LIMIT 15;
    
    COMMIT;
END$$

DELIMITER ;