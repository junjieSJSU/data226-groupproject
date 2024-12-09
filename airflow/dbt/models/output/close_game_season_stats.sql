WITH close_games AS (
    SELECT
        team,
        season,
        date,
        opponent_team,
        home_away_status,
        result,
        points_scored,
        opponent_score,
        points_scored - opponent_score AS point_margin
    FROM {{ ref('team_results') }}
    WHERE ABS(points_scored - opponent_score) <= 5 -- Filter close games (margin ≤ 5 points)
)
SELECT
    team,
    season,
    COUNT(*) AS total_close_games,
    SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS close_game_wins,
    SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) AS close_game_losses,
    ROUND(AVG(points_scored), 2) AS avg_points_scored_close_games,
    ROUND(AVG(opponent_score), 2) AS avg_points_allowed_close_games,
    ROUND(SUM(CASE WHEN result = 'win' THEN points_scored ELSE 0 END) 
          / NULLIF(SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END), 0), 2) AS avg_ppg_in_close_wins,
    ROUND(SUM(CASE WHEN result = 'loss' THEN points_scored ELSE 0 END) 
          / NULLIF(SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END), 0), 2) AS avg_ppg_in_close_losses
FROM close_games
GROUP BY team, season
ORDER BY season, team