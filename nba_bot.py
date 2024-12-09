import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from datetime import datetime
import snowflake.connector
import rapidfuzz

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
snowflake_user = os.getenv('SNOWFLAKE_USER')
snowflake_pw = os.getenv('SNOWFLAKE_PW')
snowflake_acc = os.getenv('SNOWFLAKE_ACC')

intents = discord.Intents.all()


bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

TEAM_ALIASES = {
    "Boston Celtics": ["boston", "celtics", "boston celtics"],
    "Brooklyn Nets": ["brooklyn", "nets", "brooklyn nets"],
    "New York Knicks": ["new york", "knicks", "new york knicks"],
    "Philadelphia 76ers": ["philadelphia", "sixers", "76ers", "philly", "philadelphia 76ers"],
    "Toronto Raptors": ["toronto", "raptors", "toronto raptors"],
    "Chicago Bulls": ["chicago", "bulls", "chicago bulls"],
    "Cleveland Cavaliers": ["cleveland", "cavs", "cavaliers", "cleveland cavaliers"],
    "Detroit Pistons": ["detroit", "pistons", "detroit pistons"],
    "Indiana Pacers": ["indiana", "pacers", "indiana pacers"],
    "Milwaukee Bucks": ["milwaukee", "bucks", "milwaukee bucks"],
    "Atlanta Hawks": ["atlanta", "hawks", "atlanta hawks"],
    "Charlotte Hornets": ["charlotte", "hornets", "charlotte hornets"],
    "Miami Heat": ["miami", "heat", "miami heat"],
    "Orlando Magic": ["orlando", "magic", "orlando magic"],
    "Washington Wizards": ["washington", "wizards", "washington wizards"],
    "Denver Nuggets": ["denver", "nuggets", "denver nuggets"],
    "Minnesota Timberwolves": ["minnesota", "wolves", "timberwolves", "minnesota timberwolves"],
    "Oklahoma City Thunder": ["oklahoma city", "okc", "thunder", "oklahoma city thunder"],
    "Portland Trail Blazers": ["portland", "blazers", "trail blazers", "portland trail blazers"],
    "Utah Jazz": ["utah", "jazz", "utah jazz"],
    "Golden State Warriors": ["golden state", "warriors", "gsw", "golden state warriors"],
    "Los Angeles Clippers": ["clippers", "la clippers", "los angeles clippers"],
    "Los Angeles Lakers": ["lakers", "la lakers", "los angeles lakers"],
    "Phoenix Suns": ["phoenix", "suns", "phoenix suns"],
    "Sacramento Kings": ["sacramento", "kings", "sacramento kings"],
    "Dallas Mavericks": ["dallas", "mavs", "mavericks", "dallas mavericks"],
    "Houston Rockets": ["houston", "rockets", "houston rockets"],
    "Memphis Grizzlies": ["memphis", "grizzlies", "grizz", "memphis grizzlies"],
    "New Orleans Pelicans": ["new orleans", "pelicans", "pels", "new orleans pelicans"],
    "San Antonio Spurs": ["san antonio", "spurs", "san antonio spurs"],
}

def get_standardized_team_name(input_name):
    input_name = input_name.lower()
    possible_matches = {alias: team for team, aliases in TEAM_ALIASES.items() for alias in aliases}
    best_match, score, _ = rapidfuzz.process.extractOne(input_name, possible_matches.keys())

    if score > 70:  # Adjust the threshold based on desired sensitivity
        return possible_matches[best_match]
    return None

# Helper function to validate and format the season
def get_season(year):
    if "-" in year:
        return year  # Already a valid two-year season
    try:
        start_year = int(year)
        end_year = start_year + 1
        return f"{start_year}-{end_year}"
    except ValueError:
        return None

def return_snowflake_conn():
    conn = snowflake.connector.connect(
        user=snowflake_user,
        password=snowflake_pw,
        account=snowflake_acc,
        warehouse='compute_wh',
        database='nbastats'
    )
    # Create a cursor object
    return conn.cursor()

@bot.event
async def on_ready():
    print("Bot is running.")

@bot.command(name='games')
async def games(ctx, date: str):
    cursor = return_snowflake_conn()
    try:
        # Validate the date format
        input_date = datetime.strptime(date, "%Y-%m-%d").date()

        # Query the database for games on the given date
        
        query = f"""
            SELECT season, home_team, home_score, away_team, away_score
            FROM raw_data.nba_games
            WHERE date = '{input_date}';
        """
        cursor.execute(query)
        results = cursor.fetchall()

        # Check if any games were found
        if not results:
            await ctx.send(f"No games found for {input_date}.")
            return

        # Create an embedded message
        embed = discord.Embed(
            title=f"NBA Games for {input_date}",
            color=discord.Color.blue()
        )

        # Add fields for each game
        for game in results:
            season, home_team, home_score, away_team, away_score = game
            embed.add_field(
                name=f"{home_team} vs {away_team}",
                value=f"Score: {home_score} - {away_score}",
                inline=False
            )
            
        # Send the embedded message
        embed.set_footer(text="Data retrieved from NBASTATS.RAW_DATA.NBA_GAMES")
        await ctx.send(embed=embed)

    except ValueError:
        # Invalid date format
        await ctx.send("Invalid date format. Please use yyyy-mm-dd, e.g., !games 2024-11-24.")
    except Exception as e:
        # Handle other errors
        await ctx.send(f"An error occurred: {str(e)}")
    finally:
        # Close the cursor
        cursor.close()
        
@bot.command(name='seasonperformance')
async def season_performance(ctx, *args):
    cursor = return_snowflake_conn()
    try:
        # Ensure enough arguments are provided
        if len(args) < 2:
            await ctx.send("Please provide a team name and a season year, e.g., `!seasonperformance spurs 2016`.")
            return

        # Extract team name and season from arguments
        team_name_input = " ".join(args[:-1])  # Everything except the last argument is treated as the team name
        season_input = args[-1]               # The last argument is treated as the season

        # Validate and standardize the team name
        standardized_team = get_standardized_team_name(team_name_input)
        if not standardized_team:
            await ctx.send("Invalid team name. Please check your input.")
            return

        # Validate and format the season
        formatted_season = get_season(season_input)
        if not formatted_season:
            await ctx.send("Invalid season format. Please enter a valid year, e.g., 2016.")
            return

        # Confirmation message before database call
        await ctx.send(f"Fetching performance data for {standardized_team} in the {formatted_season} season...")
        
        
        
        query = f"""
                SELECT * FROM ANALYTICS.TEAM_SEASON_STATS
                WHERE TEAM = %s AND SEASON = %s
            """
        cursor.execute(query, (standardized_team, formatted_season))
        result = cursor.fetchone()
        
        # If no results are found
        if not result:
            await ctx.send(f"No data found for `{standardized_team}` in the `{formatted_season}` season.")
            return

        # Extract the data
        (
            _, _, total_games, total_wins, total_losses, win_percentage, avg_ppg,
            avg_ppg_in_wins, avg_ppg_in_losses, avg_points_allowed,
            avg_points_allowed_in_wins, avg_points_allowed_in_losses
        ) = result

        # Create the embedded message
        embed = discord.Embed(
            title=f"{standardized_team} - {formatted_season} Season Performance",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Total Games", value=total_games, inline=True)
        embed.add_field(name="Wins", value=total_wins, inline=True)
        embed.add_field(name="Losses", value=total_losses, inline=True)
        embed.add_field(name="Win Percentage", value=f"{win_percentage*100:.1f}%", inline=False)
        embed.add_field(name="Average Points per Game (PPG)", value=avg_ppg, inline=True)
        embed.add_field(name="PPG in Wins", value=avg_ppg_in_wins, inline=True)
        embed.add_field(name="PPG in Losses", value=avg_ppg_in_losses, inline=True)
        embed.add_field(name="Points Allowed (Avg)", value=avg_points_allowed, inline=False)
        embed.add_field(name="Points Allowed in Wins (Avg)", value=avg_points_allowed_in_wins, inline=True)
        embed.add_field(name="Points Allowed in Losses (Avg)", value=avg_points_allowed_in_losses, inline=True)
        
        embed.set_footer(text="Data retrieved from NBASTATS.ANALYTICS.TEAM_SEASON_STATS")
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")
    finally:
        # Close the cursor
        cursor.close()
        
        
@bot.command(name='biggestwin')
async def season_performance(ctx, *args):
    cursor = return_snowflake_conn()
    try:
        # Ensure enough arguments are provided
        if len(args) < 2:
            await ctx.send("Please provide a team name and a season year, e.g., `!biggestwin spurs 2016`.")
            return

        # Extract team name and season from arguments
        team_name_input = " ".join(args[:-1])  # Everything except the last argument is treated as the team name
        season_input = args[-1]               # The last argument is treated as the season

        # Validate and standardize the team name
        standardized_team = get_standardized_team_name(team_name_input)
        if not standardized_team:
            await ctx.send("Invalid team name. Please check your input.")
            return

        # Validate and format the season
        formatted_season = get_season(season_input)
        if not formatted_season:
            await ctx.send("Invalid season format. Please enter a valid year, e.g., 2016.")
            return

        # Confirmation message before database call
        await ctx.send(f"Fetching the biggest win for {standardized_team} in the {formatted_season} season...")
        
        
        
        query = f"""
                SELECT * FROM ANALYTICS.TEAM_SEASON_BIGGEST_WIN_LOSS
                WHERE TEAM = %s AND SEASON = %s AND MARGIN_TYPE = 'biggest_win'
            """
        cursor.execute(query, (standardized_team, formatted_season))
        results = cursor.fetchall()
        
        # If no results are found
        if not results:
            await ctx.send(f"No biggest win data found for `{standardized_team}` in the `{formatted_season}` season.")
            return

        for result in results:
            # Extract the data
            (
                team, season, margin_type, date, opponent_team, home_away_status,
                points_scored, opponent_score, point_margin
            ) = result

            # Create the embedded message
            embed = discord.Embed(
                title=f"Biggest Win for **{standardized_team}** in the {formatted_season} season",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Date", value=date, inline=False)
            embed.add_field(name="Opponent", value=opponent_team, inline=False)
            embed.add_field(name="Home/Away", value=home_away_status.capitalize(), inline=True)
            embed.add_field(name="Points Scored", value=points_scored, inline=True)
            embed.add_field(name="Opponent Score", value=opponent_score, inline=True)
            embed.add_field(name="Margin", value=f"+{point_margin}", inline=True)
            
            embed.set_footer(text="Data retrieved from NBASTATS.ANALYTICS.TEAM_SEASON_BIGGEST_WIN_LOSS")
            await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")
    finally:
        # Close the cursor
        cursor.close()
        
        
@bot.command(name='biggestloss')
async def season_performance(ctx, *args):
    cursor = return_snowflake_conn()
    try:
        # Ensure enough arguments are provided
        if len(args) < 2:
            await ctx.send("Please provide a team name and a season year, e.g., `!biggestloss spurs 2016`.")
            return

        # Extract team name and season from arguments
        team_name_input = " ".join(args[:-1])  # Everything except the last argument is treated as the team name
        season_input = args[-1]               # The last argument is treated as the season

        # Validate and standardize the team name
        standardized_team = get_standardized_team_name(team_name_input)
        if not standardized_team:
            await ctx.send("Invalid team name. Please check your input.")
            return

        # Validate and format the season
        formatted_season = get_season(season_input)
        if not formatted_season:
            await ctx.send("Invalid season format. Please enter a valid year, e.g., 2016.")
            return

        # Confirmation message before database call
        await ctx.send(f"Fetching the biggest loss for {standardized_team} in the {formatted_season} season...")
        
        
        
        query = f"""
                SELECT * FROM ANALYTICS.TEAM_SEASON_BIGGEST_WIN_LOSS
                WHERE TEAM = %s AND SEASON = %s AND MARGIN_TYPE = 'biggest_loss'
            """
        cursor.execute(query, (standardized_team, formatted_season))
        results = cursor.fetchall()
        
        # If no results are found
        if not results:
            await ctx.send(f"No biggest loss data found for `{standardized_team}` in the `{formatted_season}` season.")
            return

        for result in results:
            # Extract the data
            (
                team, season, margin_type, date, opponent_team, home_away_status,
                points_scored, opponent_score, point_margin
            ) = result

            # Create the embedded message
            embed = discord.Embed(
                title=f"Biggest Loss for **{standardized_team}** in the {formatted_season} season",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Date", value=date, inline=False)
            embed.add_field(name="Opponent", value=opponent_team, inline=False)
            embed.add_field(name="Home/Away", value=home_away_status.capitalize(), inline=True)
            embed.add_field(name="Points Scored", value=points_scored, inline=True)
            embed.add_field(name="Opponent Score", value=opponent_score, inline=True)
            embed.add_field(name="Margin", value=f"{point_margin}", inline=True)
            
            embed.set_footer(text="Data retrieved from NBASTATS.ANALYTICS.TEAM_SEASON_BIGGEST_WIN_LOSS")
            await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")
    finally:
        # Close the cursor
        cursor.close()
        
        
        
@bot.command(name='help')
async def help_command(ctx):
    help_text = (
        "Available Commands:\n\n"
        "`!games <date>` - Get NBA games on a given date.\n"
        "Example: `!games 2024-11-24\n`"
        "• The <date> should be in YYYY-MM-DD format for the !games command.\n\n"
        "`!seasonperformance <team_name> <season>` - Get the season performance stats of a team.\n"
        "Example: `!seasonperformance spurs 2016`\n"
        "• The <team_name> can be a full team name or an alias (e.g., spurs, san antonio for San Antonio Spurs).\n"
        "• The <season> should be the year of the season (e.g., 2016 for 2016-2017).\n\n"
        "`!biggestwin <team_name> <season>` - Get the win with the largest margin for a given team for a given season.\n"
        "Example: `!biggestwin spurs 2016`\n"
        "• The <team_name> can be a full team name or an alias (e.g., spurs, san antonio for San Antonio Spurs).\n"
        "• The <season> should be the year of the season (e.g., 2016 for 2016-2017).\n\n"
        "`!biggestloss <team_name> <season>` - Get the loss with the largest margin for a given team for a given season.\n"
        "Example: `!biggestloss spurs 2016`\n"
        "• The <team_name> can be a full team name or an alias (e.g., spurs, san antonio for San Antonio Spurs).\n"
        "• The <season> should be the year of the season (e.g., 2016 for 2016-2017)."
    )
    
    await ctx.send(help_text)

        
        
bot.run(TOKEN)