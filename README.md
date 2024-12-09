# Data 226: Group Project
Instructor: Keeyong Han  
Authors: Jeff Chong, David Thach, Cyril Goud, Pranav Saravanan. 
This repository contains the files, code and images relevant to the group project of DATA 226 at San Jose State University.  
It is the collaborative work of the members of Team 9, and no one else.


# Usage Instructions
Additionally, anyone who plans to use the code are required to set up their own Alpha Vantage API key as a Snowflake Variable, and create their own Snowflake Connection object through the Airflow Connections interface.
As additional dbt libraries are used, the command 'dbt deps' will have to be executed before things can run.
A .env file with relevant credentials are required to run the Discord bot. The required credentials can be found in the bot's .py script.

# Extra Notes
As primary keys in the analytics tables are composite keys, snapshot code is written as yaml files as sql can only support single attribute unique_key.
