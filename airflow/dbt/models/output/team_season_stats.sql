SELECT
    team,
    season,
    COUNT(*) AS total_games,
    COUNT(CASE WHEN result = 'win' THEN 1 END) AS total_wins,
    COUNT(CASE WHEN result = 'loss' THEN 1 END) AS total_losses,
    ROUND((COUNT(CASE WHEN result = 'win' THEN 1 END) * 1.0) / NULLIF(COUNT(*), 0), 3) AS win_percentage,
    ROUND(AVG(points_scored), 2) AS avg_ppg, -- Average points scored per game
    ROUND(AVG(CASE WHEN result = 'win' THEN points_scored END), 2) AS avg_ppg_in_wins, -- Avg points in wins
    ROUND(AVG(CASE WHEN result = 'loss' THEN points_scored END), 2) AS avg_ppg_in_losses, -- Avg points in losses
    ROUND(AVG(opponent_score), 2) AS avg_points_allowed, -- Average points allowed per game
    ROUND(AVG(CASE WHEN result = 'win' THEN opponent_score END), 2) AS avg_points_allowed_in_wins, -- Avg points allowed in wins
    ROUND(AVG(CASE WHEN result = 'loss' THEN opponent_score END), 2) AS avg_points_allowed_in_losses -- Avg points allowed in losses
FROM {{ ref('team_results') }}
GROUP BY team, season
ORDER BY season, team