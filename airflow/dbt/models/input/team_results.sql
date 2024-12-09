-- models/input/team_results_view.sql

WITH team_game_results AS (
    SELECT
        date,
        season,
        home_team AS team,
        away_team AS opponent_team,
        'home' AS home_away_status, -- Indicating the team played at home
        CASE
            WHEN home_score > away_score THEN 'win'
            WHEN home_score < away_score THEN 'loss'
            ELSE 'draw'
        END AS result,
        home_score AS points_scored,
        away_score AS opponent_score
    FROM {{ source('raw_data', 'raw_match_data') }}

    UNION ALL

    SELECT
        date,
        season,
        away_team AS team,
        home_team AS opponent_team,
        'away' AS home_away_status, -- Indicating the team played away
        CASE
            WHEN away_score > home_score THEN 'win'
            WHEN away_score < home_score THEN 'loss'
            ELSE 'draw'
        END AS result,
        away_score AS points_scored,
        home_score AS opponent_score
    FROM {{ source('raw_data', 'raw_match_data') }}
)
SELECT 
    * 
FROM 
    team_game_results
ORDER BY 
    date, 
    team

