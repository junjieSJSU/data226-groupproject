from datetime import datetime, timedelta
from dateutil import parser
from airflow import DAG
import requests
from airflow.decorators import task
from airflow.utils.dates import days_ago
from airflow.operators.python import get_current_context
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.models import Variable


def return_snowflake_conn(con_id):
    """
    Helper function to initialize and return a Snowflake cursor.
    """
    hook = SnowflakeHook(snowflake_conn_id=con_id, warehouse='compute_wh', database='NBAstats', schema='raw_data')
    conn = hook.get_conn()
    return conn.cursor()


def get_previous_day(input_date):
    """
    Returns the previous day
    """
    previous_day = input_date - timedelta(days=1)
    return previous_day.strftime('%Y-%m-%d')

def is_utc_minus8_previous_date(iso_time: str) -> bool:
    """
    Checks if the UTC-8 equivalent of a given ISO 8601 time falls on the previous date
    relative to the UTC date.
    """
    dt_utc = parser.isoparse(iso_time)
    dt_utc_minus8 = dt_utc - timedelta(hours=8)
    
    return dt_utc_minus8.date() < dt_utc.date()


@task
def extract_data(api_key):
    """
    Extract data from the NBA API for the previous day
    """
    logical_date = get_current_context()['logical_date']
    print(f"Logical date: {logical_date}")
    previous_day = get_previous_day(logical_date)
    print(f"Previous day date: {previous_day}")
    querystring = {"date": previous_day}
    url = "https://api-nba-v1.p.rapidapi.com/games"
    headers = {
        "X-RapidAPI-Key": api_key, 
        "X-RapidAPI-Host": "api-nba-v1.p.rapidapi.com"
    }

    # Make the API request
    response = requests.get(url, headers=headers, params=querystring)

    # Check if the status code is 200 (OK)
    if response.status_code != 200:
        raise Exception(f'Request failed with status code {response.status_code}')

    result = response.json()

    # Ensure that the response contains data in the "response" key
    if "response" not in result or len(result["response"]) == 0:
        print("No game data found for the specified date.")
        return None  # No data to process

    return result


@task
def transform_data(result):
    """
    Transform the extracted data into a usable format
    """
    if result is None:  # No data to transform
        return None
    
    games = result["response"]
    games_data = []

    for game in games:
        game_data = {}
        if game["status"]["long"] == "Finished":
            if is_utc_minus8_previous_date(game["date"]["start"]):
                input_date =  datetime.strptime(result['parameters']['date'], "%Y-%m-%d")
                game_data["date"] = get_previous_day(input_date)
            else:
                game_data["date"] = result['parameters']['date']
            game_data["season"] = str(game["season"]) + "-" + str(game["season"] + 1)
            game_data["home_team"] = game["teams"]["home"]["name"]
            game_data["home_score"] = game["scores"]["home"]["points"]
            game_data["away_team"] = game["teams"]["visitors"]["name"]
            game_data["away_score"] = game["scores"]["visitors"]["points"]
            games_data.append(game_data)

    return games_data


@task
def load_data(games_data, con, target_table, staging_table):
    """
    Load the transformed data into Snowflake
    """
    if not games_data:  # No data to load
        print("No games data to load.")
        return  # Skip loading if no data
    
    try:
        con.execute("BEGIN;")
        
        create_staging_table_query = f"""
        CREATE OR REPLACE TABLE {staging_table} (
                                    date DATE,
                                    season STRING,
                                    home_team STRING,
                                    away_team STRING,
                                    home_score INT,
                                    away_score INT
        );"""
        
        cursor.execute(create_staging_table_query)
        
        insert_query = f"""INSERT INTO {staging_table}
                           (date, home_team, away_team, home_score, away_score, season)
                           VALUES (%s, %s, %s, %s, %s, %s);"""
                           
        for game in games_data:
            cursor.execute(insert_query, (
                game['date'],
                game['home_team'],
                game['away_team'],
                game['home_score'],
                game['away_score'],
                game['season']
            ))
            
        merge_query = f"""MERGE INTO {target_table} AS target
                            USING {staging_table} AS stage
                            ON target.date = stage.date
                                AND target.home_team = stage.home_team
                                AND target.away_team = stage.away_team
                            WHEN MATCHED THEN
                                UPDATE SET target.home_score = stage.home_score, 
                                        target.away_score = stage.away_score, 
                                        target.season = stage.season
                            WHEN NOT MATCHED THEN
                                INSERT (date, season, home_team, away_team, home_score, away_score)
                                VALUES (stage.date, stage.season, stage.home_team, stage.away_team, stage.home_score, stage.away_score);"""
        
        con.execute(merge_query)
        
        drop_staging_table_query = f"DROP TABLE {staging_table};"
        con.execute(drop_staging_table_query)
        
        con.execute("COMMIT;")
        print("All new data loaded successfully.")
    except Exception as e:
        con.execute("ROLLBACK;")
        print(f"An error occurred: {e}")
        raise e


with DAG(
    dag_id='nba_games_etl_daily',
    description='ETL pipeline to load daily NBA games data into Snowflake',
    schedule = '30 2 * * *',
    start_date=days_ago(1),
    catchup=False,
    tags=['ETL']
) as dag:
    target_table = 'nba_games'
    staging_table = 'nba_games_staging'
    cursor = return_snowflake_conn('snowflake_conn_nba')
    rapid_api_key = Variable.get("rapid_api_key")
    
    
    raw_data = extract_data(rapid_api_key)
    data = transform_data(raw_data)
    load_data(data, cursor, target_table, staging_table)
    
    