
import csv
import os
from datetime import datetime
from dotenv import load_dotenv

import mysql.connector
from mysql.connector import Error

load_dotenv()

# -----------------------------
# Helpers
# -----------------------------

def get_conn():
    """Create a DB connection using .env (same style as your load_players.py)."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "TRANSFERMARKT"),
    )

def parse_int(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return int(float(s))  # handles "12.0" etc.
    except ValueError:
        return None

def parse_float(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None

def parse_str(v, max_len=None):
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    if max_len is not None and len(s) > max_len:
        return s[:max_len]
    return s

def parse_date(date_string):
    """
    Accepts:
      - 'YYYY-MM-DD'
      - 'YYYY-MM-DD HH:MM:SS'
      - 'DD/MM/YYYY'
    Returns 'YYYY-MM-DD' or None.
    """
    if not date_string or not str(date_string).strip():
        return None

    s = str(date_string).strip()
    if " " in s:
        s = s.split(" ")[0]

    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    print(f"Warning: Could not parse date: {s}")
    return None

def commit_every(conn, inserted_count, batch=100):
    if inserted_count > 0 and inserted_count % batch == 0:
        conn.commit()
        print(f"Inserted {inserted_count} rows so far...")

def get_max_id(cursor, table, id_col):
    cursor.execute(f"SELECT MAX({id_col}) FROM {table}")
    res = cursor.fetchone()
    return res[0] if res and res[0] is not None else 0

# -----------------------------
# Loaders (FK order)
#   1) Clubs
#   2) Competitions
#   3) Players
#   4) Games
#   5) Transfers
# -----------------------------

def load_clubs_from_csv(csv_file_path):
    """
    Clubs(club_id PK, club_code, name, squad_size, average_age, stadium_name, stadium_seats, url)
    club_id is REQUIRED.
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO Clubs (
                club_id, club_code, name, squad_size, average_age,
                stadium_name, stadium_seats, url
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        inserted, skipped, errors = 0, 0, 0

        with open(csv_file_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    club_id = parse_int(row.get("club_id"))
                    name = parse_str(row.get("name"), 255)

                    if club_id is None or not name:
                        skipped += 1
                        continue

                    values = (
                        club_id,
                        parse_str(row.get("club_code"), 100),
                        name,
                        parse_int(row.get("squad_size")) or 0,
                        parse_float(row.get("average_age")),
                        parse_str(row.get("stadium_name"), 255),
                        parse_int(row.get("stadium_seats")),
                        parse_str(row.get("url"), 500),
                    )

                    cursor.execute(insert_query, values)
                    inserted += 1
                    commit_every(conn, inserted)

                except mysql.connector.IntegrityError as e:
                    # Duplicate PK or FK issues
                    if "Duplicate entry" in str(e):
                        # If you prefer to ignore duplicates:
                        skipped += 1
                    else:
                        print(f"Integrity error (Clubs): {e}")
                        errors += 1
                except Exception as e:
                    print(f"Error inserting club row: {e}")
                    errors += 1

        conn.commit()
        print("\n=== Clubs Import Summary ===")
        print(f"Inserted: {inserted}")
        print(f"Skipped:  {skipped}")
        print(f"Errors:   {errors}")

        cursor.close()
        conn.close()

    except Error as e:
        print(f"Database error (Clubs): {e}")
    except FileNotFoundError:
        print(f"CSV file not found: {csv_file_path}")


def load_competitions_from_csv(csv_file_path):
    """
    Competitions(competition_id PK, competition_name, competition_sub_type, competition_type, country_name)
    competition_id is REQUIRED.
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO Competitions (
                competition_id, competition_name, competition_sub_type, competition_type, country_name
            )
            VALUES (%s, %s, %s, %s, %s)
        """

        inserted, skipped, errors = 0, 0, 0

        with open(csv_file_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    competition_id = parse_str(row.get("competition_id"), 10)
                    if not competition_id:
                        skipped += 1
                        continue

                    values = (
                        competition_id,
                        parse_str(row.get("name"), 20),
                        parse_str(row.get("sub_type"), 20),
                        parse_str(row.get("type"), 20),
                        parse_str(row.get("country_name"), 10),
                    )

                    cursor.execute(insert_query, values)
                    inserted += 1
                    commit_every(conn, inserted)

                except mysql.connector.IntegrityError as e:
                    if "Duplicate entry" in str(e):
                        skipped += 1
                    else:
                        print(f"Integrity error (Competitions): {e}")
                        errors += 1
                except Exception as e:
                    print(f"Error inserting competition row: {e}")
                    errors += 1

        conn.commit()
        print("\n=== Competitions Import Summary ===")
        print(f"Inserted: {inserted}")
        print(f"Skipped:  {skipped}")
        print(f"Errors:   {errors}")

        cursor.close()
        conn.close()

    except Error as e:
        print(f"Database error (Competitions): {e}")
    except FileNotFoundError:
        print(f"CSV file not found: {csv_file_path}")


def load_players_from_csv(csv_file_path):
    """
    This is a cleaned-up equivalent of your load_players.py:
    Players(player_id PK AUTO_INCREMENT, name, current_club_id FK->Clubs, last_season, ...)
    - If CSV contains player_id, we try to use it (and fix duplicates).
    - Otherwise we allocate new IDs starting from MAX(player_id).
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()

        max_id = get_max_id(cursor, "Players", "player_id")
        print(f"Current max player_id in database: {max_id}")

        insert_query = """
            INSERT INTO Players (
                player_id, name, current_club_id, last_season, country_of_citizenship,
                date_of_birth, position, sub_position, foot, market_value, image_url
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        inserted, skipped, errors = 0, 0, 0
        used_ids = set()

        with open(csv_file_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    name = parse_str(row.get("name"), 100)
                    if not name:
                        skipped += 1
                        continue

                    csv_player_id = parse_int(row.get("player_id"))

                    if csv_player_id is None or csv_player_id in used_ids:
                        max_id += 1
                        player_id = max_id
                    else:
                        player_id = csv_player_id
                        if player_id > max_id:
                            max_id = player_id

                    used_ids.add(player_id)

                    values = (
                        player_id,
                        name,
                        parse_int(row.get("current_club_id")),
                        parse_int(row.get("last_season")),
                        parse_str(row.get("country_of_citizenship"), 50),
                        parse_date(row.get("date_of_birth")),
                        parse_str(row.get("position"), 50),
                        parse_str(row.get("sub_position"), 50),
                        parse_str(row.get("foot"), 10),
                        # CSV might have market_value_in_eur like in Transfermarkt datasets
                        parse_float(row.get("market_value")) if row.get("market_value") else parse_float(row.get("market_value_in_eur")),
                        parse_str(row.get("image_url"), 500),
                    )

                    cursor.execute(insert_query, values)
                    inserted += 1
                    commit_every(conn, inserted)

                except mysql.connector.IntegrityError as e:
                    if "Duplicate entry" in str(e):
                        # Allocate a fresh ID and retry once
                        max_id += 1
                        player_id = max_id
                        values = (player_id,) + values[1:]
                        try:
                            cursor.execute(insert_query, values)
                            inserted += 1
                        except Exception as e2:
                            print(f"Retry failed (Players): {e2}")
                            errors += 1
                    else:
                        print(f"Integrity error (Players): {e}")
                        errors += 1
                except Exception as e:
                    print(f"Error inserting player row: {e}")
                    errors += 1

        conn.commit()

        # Align AUTO_INCREMENT so next insert won't collide
        cursor.execute(f"ALTER TABLE Players AUTO_INCREMENT = {max_id + 1}")
        conn.commit()

        print("\n=== Players Import Summary ===")
        print(f"Inserted: {inserted}")
        print(f"Skipped:  {skipped}")
        print(f"Errors:   {errors}")
        print(f"Next player_id: {max_id + 1}")

        cursor.close()
        conn.close()

    except Error as e:
        print(f"Database error (Players): {e}")
    except FileNotFoundError:
        print(f"CSV file not found: {csv_file_path}")


def load_games_from_csv(csv_file_path):
    """
    Games(game_id PK AUTO_INCREMENT, home_club_id FK->Clubs, away_club_id FK->Clubs, ..., competition_id FK->Competitions)

    We support two modes:
      - If CSV has game_id: insert with explicit game_id (and fix duplicates like Players)
      - Else: insert without game_id and let AUTO_INCREMENT handle it
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()

        # detect if CSV has 'game_id'
        with open(csv_file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []

        has_game_id = "game_id" in fieldnames

        if has_game_id:
            max_id = get_max_id(cursor, "Games", "game_id")
            print(f"Current max game_id in database: {max_id}")
            used_ids = set()

            insert_query = """
                INSERT INTO Games (
                    game_id, home_club_id, away_club_id, season, date,
                    home_club_goals, away_club_goals, stadium, attendance, competition_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        else:
            insert_query = """
                INSERT INTO Games (
                    home_club_id, away_club_id, season, date,
                    home_club_goals, away_club_goals, stadium, attendance, competition_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

        inserted, skipped, errors = 0, 0, 0

        with open(csv_file_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    # minimal FK sanity: clubs + competition can be NULL? In schema: they are nullable,
                    # but FK constraints will fail if non-null and not found.
                    home_club_id = parse_int(row.get("home_club_id"))
                    away_club_id = parse_int(row.get("away_club_id"))
                    competition_id = parse_str(row.get("competition_id"), 10)

                    if has_game_id:
                        csv_game_id = parse_int(row.get("game_id"))

                        if csv_game_id is None or csv_game_id in used_ids:
                            max_id += 1
                            game_id = max_id
                        else:
                            game_id = csv_game_id
                            if game_id > max_id:
                                max_id = game_id

                        used_ids.add(game_id)

                        values = (
                            game_id,
                            home_club_id,
                            away_club_id,
                            parse_int(row.get("season")),
                            parse_date(row.get("date")),
                            parse_int(row.get("home_club_goals")),
                            parse_int(row.get("away_club_goals")),
                            parse_str(row.get("stadium"), 100),
                            parse_int(row.get("attendance")),
                            competition_id,
                        )
                    else:
                        values = (
                            home_club_id,
                            away_club_id,
                            parse_int(row.get("season")),
                            parse_date(row.get("date")),
                            parse_int(row.get("home_club_goals")),
                            parse_int(row.get("away_club_goals")),
                            parse_str(row.get("stadium"), 100),
                            parse_int(row.get("attendance")),
                            competition_id,
                        )

                    cursor.execute(insert_query, values)
                    inserted += 1
                    commit_every(conn, inserted)

                except mysql.connector.IntegrityError as e:
                    if "Duplicate entry" in str(e) and has_game_id:
                        max_id += 1
                        game_id = max_id
                        values = (game_id,) + values[1:]
                        try:
                            cursor.execute(insert_query, values)
                            inserted += 1
                        except Exception as e2:
                            print(f"Retry failed (Games): {e2}")
                            errors += 1
                    else:
                        print(f"Integrity error (Games): {e}")
                        errors += 1
                except Exception as e:
                    print(f"Error inserting game row: {e}")
                    errors += 1

        conn.commit()

        if has_game_id:
            cursor.execute(f"ALTER TABLE Games AUTO_INCREMENT = {max_id + 1}")
            conn.commit()
            print(f"Next game_id: {max_id + 1}")

        print("\n=== Games Import Summary ===")
        print(f"Inserted: {inserted}")
        print(f"Skipped:  {skipped}")
        print(f"Errors:   {errors}")

        cursor.close()
        conn.close()

    except Error as e:
        print(f"Database error (Games): {e}")
    except FileNotFoundError:
        print(f"CSV file not found: {csv_file_path}")


def load_transfers_from_csv(csv_file_path):
    """
    Transfers(transfer_id PK AUTO_INCREMENT, player_id FK->Players, from_club_id FK->Clubs, to_club_id FK->Clubs, ...)

    Supports two modes:
      - If CSV has transfer_id: insert with explicit transfer_id (and fix duplicates)
      - Else: let AUTO_INCREMENT handle it
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()

        with open(csv_file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []

        has_transfer_id = "transfer_id" in fieldnames

        if has_transfer_id:
            max_id = get_max_id(cursor, "Transfers", "transfer_id")
            print(f"Current max transfer_id in database: {max_id}")
            used_ids = set()

            insert_query = """
                INSERT INTO Transfers (
                    transfer_id, player_id, transfer_date, transfer_season,
                    from_club_id, to_club_id, from_club_name, to_club_name,
                    transfer_fee, market_value_in_eur, player_name
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        else:
            insert_query = """
                INSERT INTO Transfers (
                    player_id, transfer_date, transfer_season,
                    from_club_id, to_club_id, from_club_name, to_club_name,
                    transfer_fee, market_value_in_eur, player_name
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

        inserted, skipped, errors = 0, 0, 0

        with open(csv_file_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    transfer_season = parse_str(row.get("transfer_season"), 50)
                    player_name = parse_str(row.get("player_name"), 100)

                    # These are NOT NULL in schema (transfer_season, player_name)
                    if not transfer_season or not player_name:
                        skipped += 1
                        continue

                    if has_transfer_id:
                        csv_transfer_id = parse_int(row.get("transfer_id"))
                        if csv_transfer_id is None or csv_transfer_id in used_ids:
                            max_id += 1
                            transfer_id = max_id
                        else:
                            transfer_id = csv_transfer_id
                            if transfer_id > max_id:
                                max_id = transfer_id
                        used_ids.add(transfer_id)

                        values = (
                            transfer_id,
                            parse_int(row.get("player_id")),
                            parse_date(row.get("transfer_date")),
                            transfer_season,
                            parse_int(row.get("from_club_id")),
                            parse_int(row.get("to_club_id")),
                            parse_str(row.get("from_club_name"), 100),
                            parse_str(row.get("to_club_name"), 100),
                            parse_float(row.get("transfer_fee")),
                            parse_float(row.get("market_value_in_eur")),
                            player_name,
                        )
                    else:
                        values = (
                            parse_int(row.get("player_id")),
                            parse_date(row.get("transfer_date")),
                            transfer_season,
                            parse_int(row.get("from_club_id")),
                            parse_int(row.get("to_club_id")),
                            parse_str(row.get("from_club_name"), 100),
                            parse_str(row.get("to_club_name"), 100),
                            parse_float(row.get("transfer_fee")),
                            parse_float(row.get("market_value_in_eur")),
                            player_name,
                        )

                    cursor.execute(insert_query, values)
                    inserted += 1
                    commit_every(conn, inserted)

                except mysql.connector.IntegrityError as e:
                    if "Duplicate entry" in str(e) and has_transfer_id:
                        max_id += 1
                        transfer_id = max_id
                        values = (transfer_id,) + values[1:]
                        try:
                            cursor.execute(insert_query, values)
                            inserted += 1
                        except Exception as e2:
                            print(f"Retry failed (Transfers): {e2}")
                            errors += 1
                    else:
                        print(f"Integrity error (Transfers): {e}")
                        errors += 1
                except Exception as e:
                    print(f"Error inserting transfer row: {e}")
                    errors += 1

        conn.commit()

        if has_transfer_id:
            cursor.execute(f"ALTER TABLE Transfers AUTO_INCREMENT = {max_id + 1}")
            conn.commit()
            print(f"Next transfer_id: {max_id + 1}")

        print("\n=== Transfers Import Summary ===")
        print(f"Inserted: {inserted}")
        print(f"Skipped:  {skipped}")
        print(f"Errors:   {errors}")

        cursor.close()
        conn.close()

    except Error as e:
        print(f"Database error (Transfers): {e}")
    except FileNotFoundError:
        print(f"CSV file not found: {csv_file_path}")


def load_all_from_csv(
    clubs_csv,
    competitions_csv,
    players_csv,
    games_csv,
    transfers_csv,
):
    """
    FK-safe load order:
      Clubs -> Competitions -> Players -> Games -> Transfers
    """
    load_clubs_from_csv(clubs_csv)
    load_competitions_from_csv(competitions_csv)
    load_players_from_csv(players_csv)
    load_games_from_csv(games_csv)
    load_transfers_from_csv(transfers_csv)


if __name__ == "__main__":
    # Update these paths to your local CSV paths
    clubs_csv = r"C:\Users\cagsak\Desktop\clubs.csv"
    competitions_csv = r"C:\Users\cagsak\Desktop\competitions.csv"
    players_csv = r"C:\Users\cagsak\Desktop\players.csv"
    games_csv = r"C:\Users\cagsak\Desktop\games.csv"
    transfers_csv = r"C:\Users\cagsak\Desktop\transfers.csv"

    load_all_from_csv(
        clubs_csv=clubs_csv,
        competitions_csv=competitions_csv,
        players_csv=players_csv,
        games_csv=games_csv,
        transfers_csv=transfers_csv,
    )
