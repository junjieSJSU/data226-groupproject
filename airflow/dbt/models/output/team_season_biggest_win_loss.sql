WITH team_performance AS (
    SELECT
        team,
        season,
        date,
        opponent_team,
        home_away_status,
        points_scored,
        opponent_score,
        points_scored - opponent_score AS point_margin
    FROM {{ ref('team_results') }}
),
largest_margins AS (
    SELECT
        team,
        season,
        MAX(point_margin) AS biggest_win,
        MIN(point_margin) AS biggest_loss
    FROM team_performance
    GROUP BY team, season
),
extreme_margins AS (
    SELECT DISTINCT
        tp.team,
        tp.season,
        tp.date,
        tp.opponent_team,
        tp.home_away_status,
        tp.points_scored,
        tp.opponent_score,
        tp.point_margin,
        CASE
            WHEN tp.point_margin = lm.biggest_win THEN 'biggest_win'
            WHEN tp.point_margin = lm.biggest_loss THEN 'biggest_loss'
        END AS margin_type
    FROM team_performance tp
    JOIN largest_margins lm
        ON tp.team = lm.team
        AND tp.season = lm.season
        AND (tp.point_margin = lm.biggest_win OR tp.point_margin = lm.biggest_loss)
)
SELECT
    team,
    season,
    margin_type,  -- 'biggest_win' or 'biggest_loss'
    date,
    opponent_team,
    home_away_status,
    points_scored,
    opponent_score,
    point_margin
FROM extreme_margins
ORDER BY season, team, margin_type DESC
