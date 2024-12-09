from airflow import DAG
from airflow.decorators import task
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from airflow.utils.dates import days_ago
import os


def return_snowflake_conn(con_id):
    """
    Helper function to initialize and return a Snowflake cursor.
    """
    hook = SnowflakeHook(snowflake_conn_id=con_id, warehouse='compute_wh', database='NBAstats', schema='raw_data')
    conn = hook.get_conn()
    return conn.cursor()


@task
def stage_file_to_snowflake(local_file_path, snowflake_stage, con):
    """
    Upload the CSV file to a Snowflake stage.
    """
    try:
        # Ensure the file exists
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"The file {local_file_path} does not exist.")

        con.execute("BEGIN;")

        # Upload file to the Snowflake stage
        con.execute(f"PUT file://{local_file_path} @{snowflake_stage} AUTO_COMPRESS=TRUE;")
        
        con.execute("COMMIT;")
        print(f"File {local_file_path} successfully staged to {snowflake_stage}.")
        
    except Exception as e:
        con.execute("ROLLBACK;")
        print(f"Error staging file: {e}")
        raise e

@task
def load_data_to_snowflake(snowflake_stage, target_table, con):
    """
    Create a table and load the data from the staged file into the target table using COPY INTO.
    """
    
    create_table_query = f"""
    CREATE OR REPLACE TABLE {target_table} (
        date DATE,
        season VARCHAR,
        home_team VARCHAR,
        away_team VARCHAR,
        home_score INTEGER,
        away_score INTEGER
    );
    """
    
    copy_query = f"""
    COPY INTO {target_table}
    FROM @{snowflake_stage}
    FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);
    """
    
    try:
        con.execute("BEGIN;")
        con.execute(create_table_query)
        con.execute(copy_query)
        print(f"Data successfully loaded into a new table {target_table}.")
        con.execute("COMMIT;")
    except Exception as e:
        con.execute("ROLLBACK;")
        print(f"Error loading data to Snowflake: {e}")
        raise e


# Define the DAG
with DAG(
    dag_id='nba_games_etl_historical',
    description='ETL pipeline to load NBA games data into Snowflake',
    schedule_interval=None,
    start_date=days_ago(1),
    catchup=False,
    tags=['ETL'],
) as dag:
    # Variables
    local_file_path = '/opt/airflow/data/raw_data_games.csv'
    snowflake_stage = 'raw_data_stage'             # Replace with your Snowflake stage
    target_table = 'NBAstats.raw_data.nba_games'
    cursor = return_snowflake_conn('snowflake_conn_nba')

    # Tasks
    stage_file = stage_file_to_snowflake(local_file_path, snowflake_stage, cursor)
    load_data = load_data_to_snowflake(snowflake_stage, target_table, cursor)

    # Task dependencies
    stage_file >> load_data
