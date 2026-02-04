from flask import Blueprint, render_template, jsonify, request
from app.db import get_db_connection
from mysql.connector import Error

games_bp = Blueprint('games', __name__)

@games_bp.route("/games")
def manage_games_page():
    return render_template("games.html")

@games_bp.route("/api/clubs", methods=["GET"])
def get_clubs():
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT club_id, name FROM Clubs ORDER BY name") 
        clubs = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(clubs)
    except Error as e:
        print(f"Error fetching clubs: {e}")
        return jsonify({"error": "Failed to retrieve clubs"}), 500

@games_bp.route("/api/competitions", methods=["GET"])
def get_competitions():
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT competition_id, competition_name FROM Competitions ORDER BY competition_name")
        competitions = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(competitions)
    except Error as e:
        print(f"Error fetching competitions: {e}")
        return jsonify({"error": "Failed to retrieve competitions"}), 500

@games_bp.route("/api/games", methods=["GET"])
def get_games():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 10
    offset = (page - 1) * per_page

    # Filters
    home_filter = request.args.get("home", type=str)
    away_filter = request.args.get("away", type=str)
    season_filter = request.args.get("season", type=str)
    competition_filter = request.args.get("competition", type=str)
    date_from = request.args.get("date_from", type=str)
    date_to = request.args.get("date_to", type=str)
    sort = request.args.get("sort", default="date", type=str)
    order = request.args.get("order", default="desc", type=str).lower()
    
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
        cursor = conn.cursor(dictionary=True)

        # Build WHERE dynamically
        where_clauses = []
        params = []

        if home_filter:
            where_clauses.append("hc.name LIKE %s")
            params.append(f"%{home_filter}%")
        if away_filter:
            where_clauses.append("ac.name LIKE %s")
            params.append(f"%{away_filter}%")
        if season_filter:
            where_clauses.append("g.season = %s")
            params.append(season_filter)
        if competition_filter:
            where_clauses.append("g.competition_id = %s")
            params.append(competition_filter)
        if date_from:
            where_clauses.append("g.date >= %s")
            params.append(date_from)
        if date_to:
            where_clauses.append("g.date <= %s")
            params.append(date_to)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Sorting whitelist
        sort_map = {
            "date": "g.date",
            "season": "g.season",
            "home_club": "hc.name",
            "away_club": "ac.name",
            "competition": "g.competition_id",
            "home_goals": "g.home_club_goals",
            "away_goals": "g.away_club_goals",
            "stadium": "g.stadium",
            "attendance": "g.attendance",
        }
        sort_col = sort_map.get(sort, "g.date")
        if sort_col == "g.home_club_goals":
            sort_col = "(g.home_club_goals + g.away_club_goals)"
        sort_dir = "ASC" if order == "asc" else "DESC"

        # Total count for pagination
        count_query = f"""
            SELECT COUNT(*) AS total
            FROM Games g
            JOIN Clubs hc ON g.home_club_id = hc.club_id
            JOIN Clubs ac ON g.away_club_id = ac.club_id
            {where_sql}
        """
        cursor.execute(count_query, tuple(params))
        total_count_row = cursor.fetchone() or {"total": 0}
        total_count = total_count_row["total"]

        query = f"""
            SELECT 
                g.game_id, g.date, 
                g.home_club_id, g.away_club_id,
                hc.name AS home_club, ac.name AS away_club, 
                g.home_club_goals, g.away_club_goals, g.season, g.competition_id,
                g.stadium, g.attendance
            FROM Games g
            JOIN Clubs hc ON g.home_club_id = hc.club_id
            JOIN Clubs ac ON g.away_club_id = ac.club_id
            {where_sql}
            ORDER BY {sort_col} {sort_dir}, g.game_id DESC
            LIMIT %s OFFSET %s
        """

        cursor.execute(query, tuple(params + [per_page, offset]))
        games = cursor.fetchall()
        cursor.close()
        conn.close()
        total_pages = (total_count + per_page - 1) // per_page if per_page else 1
        return jsonify({
            "games": games,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count
        })
    except Error as e:
        print(f"Error fetching games: {e}")
        return jsonify({"error": "Failed to retrieve games"}), 500


@games_bp.route("/api/games/head2head", methods=["GET"])
def head_to_head():
    home_id = request.args.get("home_id", type=int)
    away_id = request.args.get("away_id", type=int)

    if not home_id or not away_id or home_id == away_id:
        return jsonify({"error": "home_id and away_id are required and must be different"}), 400

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = conn.cursor(dictionary=True)

        # Fetch club basic info
        cursor.execute(
            """
            SELECT 
                c.club_id, c.name, c.squad_size, c.average_age,
                (SELECT COUNT(*) FROM Players p WHERE p.current_club_id = c.club_id) AS player_count,
                (SELECT COALESCE(SUM(p.market_value), 0) FROM Players p WHERE p.current_club_id = c.club_id) AS total_value,
                (SELECT AVG(p.market_value) FROM Players p WHERE p.current_club_id = c.club_id) AS avg_value
            FROM Clubs c
            WHERE c.club_id IN (%s, %s)
            """,
            (home_id, away_id),
        )
        clubs_raw = cursor.fetchall() or []
        club_info = {row["club_id"]: row for row in clubs_raw}

        # Last 5 head-to-head games
        cursor.execute(
            """
            SELECT 
                g.game_id, g.date, g.season,
                g.home_club_id, g.away_club_id,
                hc.name AS home_club, ac.name AS away_club,
                g.home_club_goals, g.away_club_goals,
                ABS(g.home_club_goals - g.away_club_goals) AS goal_diff
            FROM Games g
            JOIN Clubs hc ON g.home_club_id = hc.club_id
            JOIN Clubs ac ON g.away_club_id = ac.club_id
            WHERE (g.home_club_id = %s AND g.away_club_id = %s)
               OR (g.home_club_id = %s AND g.away_club_id = %s)
            ORDER BY g.date DESC
            LIMIT 5
            """,
            (home_id, away_id, away_id, home_id),
        )
        last_games = cursor.fetchall() or []

        # Summary stats
        cursor.execute(
            """
            SELECT
                COUNT(*) AS matches,
                SUM(
                    CASE 
                        WHEN (g.home_club_id = %s AND g.home_club_goals > g.away_club_goals)
                          OR (g.away_club_id = %s AND g.away_club_goals > g.home_club_goals)
                        THEN 1 ELSE 0 END
                ) AS home_wins,
                SUM(
                    CASE 
                        WHEN (g.home_club_id = %s AND g.home_club_goals > g.away_club_goals)
                          OR (g.away_club_id = %s AND g.away_club_goals > g.home_club_goals)
                        THEN 1 ELSE 0 END
                ) AS away_wins,
                SUM(CASE WHEN g.home_club_goals = g.away_club_goals THEN 1 ELSE 0 END) AS draws,
                SUM(
                    CASE 
                        WHEN g.home_club_id = %s THEN g.home_club_goals
                        WHEN g.away_club_id = %s THEN g.away_club_goals
                        ELSE 0 END
                ) AS home_goals,
                SUM(
                    CASE 
                        WHEN g.home_club_id = %s THEN g.home_club_goals
                        WHEN g.away_club_id = %s THEN g.away_club_goals
                        ELSE 0 END
                ) AS away_goals,
                AVG(g.home_club_goals + g.away_club_goals) AS avg_goals,
                AVG(g.attendance) AS avg_attendance
            FROM Games g
            WHERE (g.home_club_id = %s AND g.away_club_id = %s)
               OR (g.home_club_id = %s AND g.away_club_id = %s)
            """,
            (
                home_id, home_id,  # home wins
                away_id, away_id,  # away wins
                home_id, home_id,  # home goals
                away_id, away_id,  # away goals
                home_id, away_id, away_id, home_id,  # filter
            ),
        )
        summary_row = cursor.fetchone() or {}

        # Biggest win (highest goal difference)
        cursor.execute(
            """
            SELECT 
                g.game_id, g.date, g.season,
                g.home_club_id, g.away_club_id,
                hc.name AS home_club, ac.name AS away_club,
                g.home_club_goals, g.away_club_goals,
                (g.home_club_goals - g.away_club_goals) AS diff
            FROM Games g
            JOIN Clubs hc ON g.home_club_id = hc.club_id
            JOIN Clubs ac ON g.away_club_id = ac.club_id
            WHERE (g.home_club_id = %s AND g.away_club_id = %s)
               OR (g.home_club_id = %s AND g.away_club_id = %s)
            ORDER BY ABS(g.home_club_goals - g.away_club_goals) DESC, g.date DESC
            LIMIT 1
            """,
            (home_id, away_id, away_id, home_id),
        )
        biggest_win = cursor.fetchone()

        # Most expensive transfer between the two clubs (any direction)
        cursor.execute(
            """
            SELECT 
                t.transfer_id, t.player_name, t.transfer_fee, t.transfer_date, t.transfer_season,
                t.from_club_id, t.to_club_id, t.from_club_name, t.to_club_name
            FROM Transfers t
            WHERE (t.from_club_id = %s AND t.to_club_id = %s)
               OR (t.from_club_id = %s AND t.to_club_id = %s)
            ORDER BY t.transfer_fee DESC
            LIMIT 1
            """,
            (home_id, away_id, away_id, home_id),
        )
        top_transfer = cursor.fetchone()

        cursor.close()
        conn.close()

        # Safe defaults
        matches = summary_row.get("matches") or 0
        response = {
            "clubs": {
                "home": {
                    "id": home_id,
                    "name": club_info.get(home_id, {}).get("name"),
                    "squad_size": club_info.get(home_id, {}).get("squad_size"),
                    "average_age": club_info.get(home_id, {}).get("average_age"),
                    "players": club_info.get(home_id, {}).get("player_count"),
                    "total_value": club_info.get(home_id, {}).get("total_value"),
                    "avg_value": club_info.get(home_id, {}).get("avg_value"),
                },
                "away": {
                    "id": away_id,
                    "name": club_info.get(away_id, {}).get("name"),
                    "squad_size": club_info.get(away_id, {}).get("squad_size"),
                    "average_age": club_info.get(away_id, {}).get("average_age"),
                    "players": club_info.get(away_id, {}).get("player_count"),
                    "total_value": club_info.get(away_id, {}).get("total_value"),
                    "avg_value": club_info.get(away_id, {}).get("avg_value"),
                },
            },
            "last_games": last_games,
            "summary": {
                "matches": matches,
                "home_wins": summary_row.get("home_wins") or 0,
                "away_wins": summary_row.get("away_wins") or 0,
                "draws": summary_row.get("draws") or 0,
                "home_goals": summary_row.get("home_goals") or 0,
                "away_goals": summary_row.get("away_goals") or 0,
                "avg_goals": summary_row.get("avg_goals") or 0,
                "avg_attendance": summary_row.get("avg_attendance") or 0,
            },
            "biggest_win": biggest_win,
            "top_transfer": top_transfer,
        }

        return jsonify(response)
    except Error as e:
        print(f"Error fetching head-to-head: {e}")
        return jsonify({"error": "Failed to retrieve head-to-head stats"}), 500

@games_bp.route("/api/games/<int:game_id>", methods=["GET"])
def get_game_details(game_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Games WHERE game_id = %s", (game_id,))
        game = cursor.fetchone()
        cursor.close()
        conn.close()
        if game:
            return jsonify(game)
        return jsonify({"error": "Game not found"}), 404
    except Error as e:
        print(f"Error fetching game details: {e}")
        return jsonify({"error": "Failed to retrieve game details"}), 500

@games_bp.route("/api/games/add", methods=["POST"])
def add_game():
    data = request.get_json()
    required_fields = ['home_club_id', 'away_club_id', 'season', 'date', 'home_club_goals', 'away_club_goals', 'competition_id']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
        cursor = conn.cursor()
        query = """
            INSERT INTO Games (home_club_id, away_club_id, season, date, home_club_goals, away_club_goals, stadium, attendance, competition_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data['home_club_id'], data['away_club_id'], data['season'], data['date'], 
            data['home_club_goals'], data['away_club_goals'], data.get('stadium'), data.get('attendance'), data['competition_id']
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Game added successfully"})
    except Error as e:
        print(f"Error adding game: {e}")
        return jsonify({"error": str(e)}), 500

@games_bp.route("/api/games/update/<int:game_id>", methods=["PUT"])
def update_game(game_id):
    data = request.get_json()
    
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = conn.cursor()
        query = """
            UPDATE Games SET date=%s, season=%s, home_club_goals=%s, away_club_goals=%s, 
                         stadium=%s, attendance=%s, competition_id=%s
            WHERE game_id=%s
        """
        cursor.execute(query, (
            data['date'], data['season'], data['home_club_goals'], data['away_club_goals'],
            data.get('stadium'), data.get('attendance'), data.get('competition_id'), game_id
        ))
        conn.commit()
        
        updated_rows = cursor.rowcount
        cursor.close()
        conn.close()

        if updated_rows == 0:
            return jsonify({"error": "Game not found or no data changed"}), 404
        
        return jsonify({"success": True, "message": "Game updated successfully"})
    except Error as e:
        print(f"Error updating game: {e}")
        return jsonify({"error": str(e)}), 500

@games_bp.route("/api/games/delete/<int:game_id>", methods=["DELETE"])
def delete_game(game_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Games WHERE game_id = %s", (game_id,))
        conn.commit()
        
        deleted_rows = cursor.rowcount
        cursor.close()
        conn.close()

        if deleted_rows == 0:
            return jsonify({"error": "Game not found"}), 404
            
        return jsonify({"success": True, "message": "Game deleted successfully"})
    except Error as e:
        print(f"Error deleting game: {e}")
        return jsonify({"error": str(e)}), 500
