# services/gemini_sql.py
from google import genai
import os
from dotenv import load_dotenv
from utils.validation import is_safe_sql
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_2.5_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_2.5_API_KEY missing in environment")

client = genai.Client(api_key=GEMINI_API_KEY)


# --- Prompt template --------------------------------------------------------

SCHEMA_SNIPPET = """
TABLE competitions (
    competition_id PK, competition_code, name, sub_type, type,
    country_name, confederation, is_major_national_league
)

TABLE clubs (
    club_id PK,
    name,
    squad_size,
    average_age,
    foreigners_number,
    foreigners_percentage,
    domestic_competition_id → competitions.competition_id
)

TABLE players (
    player_id PK,
    name,
    position,
    foot,
    date_of_birth,
    country_of_birth,
    height_in_cm,
    highest_market_value_in_eur,
    current_club_id → clubs.club_id
)

TABLE games (
    game_id PK,
    competition_id → competitions.competition_id,
    season,
    date, round,
    attendance,
    stadium,
    home_club_id → clubs.club_id,
    away_club_id → clubs.club_id,
    home_club_goals, away_club_goals,
    aggregate
)

TABLE appearances (
    appearance_id PK,
    game_id   → games.game_id,
    player_id → players.player_id,
    player_club_id → clubs.club_id,
    goals, assists, minutes_played,
    yellow_cards, red_cards
)

TABLE game_lineups (
    game_lineups_id PK,
    game_id   → games.game_id,
    player_id → players.player_id,
    club_id   → clubs.club_id,
    position, type, jersey_number
)

TABLE game_events (
    game_event_id PK,
    game_id   → games.game_id,
    player_id → players.player_id,
    club_id   → clubs.club_id,
    minute, event_type
)

TABLE player_valuations (
    PK (player_id, valuation_date),
    current_club_id → clubs.club_id,
    market_value_in_eur
)
"""
PROMPT_TMPL = """
You are an expert PostgreSQL analyst.

• Use **PostgreSQL 15 syntax only**  
 - For year extraction use  `EXTRACT(YEAR FROM date_col)`  
 - Never use `strftime`, `DATE_FORMAT`, or MySQL/SQLite functions.
 - When any specific players details is asked don't directly use the player name as it is provided by the user, example "total goals scored by ronaldo in 2012" in these types of situation use ILIKE to search and enclose the name between %Ronaldo%. Use same technique for questions related to clubs or any particular teams.

Generate ONE PostgreSQL query and return ONLY the SQL (no code fences).

Schema:
{schema}

User question:
{question}

SQL:"""

# ---------------------------------------------------------------------------
def question_to_sql(question: str) -> str:
    prompt = PROMPT_TMPL.format(schema=SCHEMA_SNIPPET, question=question)
    high_temp_config = types.GenerateContentConfig(temperature=0.2)

    response = client.models.generate_content(
    model='gemini-2.5-pro-exp-03-25',
    config=high_temp_config,
    contents=prompt)

    sql = response.text.strip().strip("```sql").strip("```").strip()
    if sql.endswith(";"):
        sql = sql[:-1].strip()  
        
    if not is_safe_sql(sql):
        raise ValueError("Generated SQL failed safety check:\n" + sql)

    return sql
