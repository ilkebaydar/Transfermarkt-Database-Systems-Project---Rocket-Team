from flask import Blueprint, render_template, jsonify, request, abort
from app.db import get_db_connection
from mysql.connector import Error

clubs_bp = Blueprint('clubs', __name__)


@clubs_bp.route("/clubs")
def manage_clubs_page():
    return render_template("clubs.html")


@clubs_bp.route("/api/competitions", methods=["GET"])
def get_competitions():
    """Get all competitions for dropdown selection"""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT 
                competition_id, 
                competition_name, 
                country_name 
            FROM Competitions 
            ORDER BY country_name ASC, competition_name ASC
        """
        cursor.execute(query)
        competitions = cursor.fetchall()

        cursor.close()
        conn.close()
        return jsonify(competitions)
    except Error as e:
        print(f"Error fetching competitions: {e}")
        return jsonify({"error": "Failed to retrieve competitions"}), 500


@clubs_bp.route("/api/clubs_list", methods=["GET"])
def get_all_clubs():
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT 
                c.club_id, 
                c.club_code, 
                c.name, 
                c.squad_size, 
                c.average_age, 
                c.stadium_name, 
                c.stadium_seats, 
                c.url,
                c.competition_id,
                comp.country_name
            FROM Clubs c
            LEFT JOIN Competitions comp ON c.competition_id = comp.competition_id
            ORDER BY c.name ASC
        """
        cursor.execute(query)
        clubs = cursor.fetchall()

        cursor.close()
        conn.close()
        return jsonify(clubs)
    except Error as e:
        print(f"Error fetching clubs: {e}")
        return jsonify({"error": "Failed to retrieve clubs"}), 500


@clubs_bp.route("/api/clubs/add", methods=["POST"])
def add_club():
    data = request.get_json()

    club_id = data.get('club_id')
    club_code = data.get('club_code')
    name = data.get('name')
    competition_id = data.get('competition_id')
    squad_size = data.get('squad_size', 0)
    average_age = data.get('average_age')
    stadium_name = data.get('stadium_name')
    stadium_seats = data.get('stadium_seats')
    url = data.get('url')

    if not all([club_id, name]):
        return jsonify({"error": "Missing required fields (club_id, name)"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO Clubs (club_id, club_code, name, competition_id, squad_size, average_age, stadium_name, stadium_seats, url) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (club_id, club_code, name, competition_id, squad_size, average_age, stadium_name, stadium_seats, url))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Club added successfully"})
    except Error as e:
        print(f"Error adding club: {e}")
        return jsonify({"error": str(e)}), 500



@clubs_bp.route("/api/clubs/<int:club_id>", methods=["PUT"])
def update_club(club_id):
    data = request.get_json()
    
    name = data.get('name')
    club_code = data.get('club_code')
    competition_id = data.get('competition_id')
    squad_size = data.get('squad_size')
    average_age = data.get('average_age')
    stadium_name = data.get('stadium_name')
    stadium_seats = data.get('stadium_seats')
    url = data.get('url')

    if not name:
         return jsonify({"error": "Name field is required"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            UPDATE Clubs 
            SET name=%s, club_code=%s, competition_id=%s, squad_size=%s, average_age=%s, 
                stadium_name=%s, stadium_seats=%s, url=%s
            WHERE club_id=%s
        """
        
        cursor.execute(query, (name, club_code, competition_id, squad_size, average_age, stadium_name, stadium_seats, url, club_id))
        conn.commit()

        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Club updated successfully"})

    except Error as e:
        print(f"Error updating club: {e}")
        return jsonify({"error": str(e)}), 500



@clubs_bp.route("/api/clubs/<int:club_id>", methods=["DELETE"])
def delete_club(club_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "DELETE FROM Clubs WHERE club_id = %s"
        cursor.execute(query, (club_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True, "message": "Club deleted successfully"})

    except Error as e:
        print(f"Error deleting club: {e}")
        return jsonify({"error": str(e)}), 500


@clubs_bp.route("/clubs/<int:club_id>")
def club_details(club_id):
    """
    Display club details page with:
    - Club photo and basic info
    - League/competition information
    - Other teams in the same league
    - Transfers by season with fees and current market values
    """
    try:
        conn = get_db_connection()
        if conn is None:
            abort(500, description="Database connection failed")
        
        cursor = conn.cursor(dictionary=True)

        # Complex query joining 4+ tables: Clubs, Competitions, Players, Transfers
        # Gets club info and competition info
        query = """
            SELECT 
                c.club_id,
                c.name AS club_name,
                c.club_code,
                c.squad_size,
                c.average_age,
                c.stadium_name,
                c.stadium_seats,
                c.url,
                c.competition_id,
                comp.competition_name,
                comp.country_name,
                comp.competition_type,
                comp.competition_sub_type
            FROM Clubs c
            LEFT JOIN Competitions comp ON c.competition_id = comp.competition_id
            WHERE c.club_id = %s
        """
        
        cursor.execute(query, (club_id,))
        club_data = cursor.fetchone()
        
        if not club_data:
            abort(404, description=f"Club with ID {club_id} not found")
        
        # Get other clubs in the same league (competition)
        if club_data['competition_id']:
            other_clubs_query = """
                SELECT 
                    c2.club_id,
                    c2.name AS club_name,
                    c2.club_code,
                    c2.average_age,
                    c2.squad_size
                FROM Clubs c2
                WHERE c2.competition_id = %s
                AND c2.club_id != %s
                ORDER BY c2.name ASC
            """
            cursor.execute(other_clubs_query, (club_data['competition_id'], club_id))
            other_clubs = cursor.fetchall()
        else:
            other_clubs = []
        
        # Get detailed transfers with player market values (joining Transfers, Players, Clubs)
        transfers_query = """
            SELECT 
                t.transfer_id,
                t.transfer_season,
                t.transfer_date,
                t.player_name,
                t.transfer_fee,
                t.market_value_in_eur AS transfer_market_value,
                -- Join with Players table to get current market value
                p.market_value AS current_market_value,
                p.position,
                p.country_of_citizenship,
                -- Join with Clubs to get from/to club names
                from_club.name AS from_club_name,
                to_club.name AS to_club_name,
                t.from_club_id,
                t.to_club_id
            FROM Transfers t
            LEFT JOIN Players p ON t.player_id = p.player_id
            LEFT JOIN Clubs from_club ON t.from_club_id = from_club.club_id
            LEFT JOIN Clubs to_club ON t.to_club_id = to_club.club_id
            WHERE (t.from_club_id = %s OR t.to_club_id = %s)
            ORDER BY t.transfer_season DESC, t.transfer_date DESC
            LIMIT 50
        """
        cursor.execute(transfers_query, (club_id, club_id))
        transfers = cursor.fetchall()
        
        # Parse transfers by season JSON (if MySQL version supports JSON_ARRAYAGG)
        # Otherwise, we'll group transfers by season in Python
        transfers_by_season = {}
        for transfer in transfers:
            season = transfer['transfer_season']
            if season not in transfers_by_season:
                transfers_by_season[season] = {
                    'season': season,
                    'transfers': [],
                    'total_spent': 0,
                    'total_earned': 0,
                    'transfers_in_count': 0,
                    'transfers_out_count': 0
                }
            
            transfers_by_season[season]['transfers'].append(transfer)
            
            if transfer['to_club_id'] == club_id:
                transfers_by_season[season]['transfers_in_count'] += 1
                if transfer['transfer_fee']:
                    transfers_by_season[season]['total_spent'] += transfer['transfer_fee']
            elif transfer['from_club_id'] == club_id:
                transfers_by_season[season]['transfers_out_count'] += 1
                if transfer['transfer_fee']:
                    transfers_by_season[season]['total_earned'] += transfer['transfer_fee']
        
        # Convert to list and sort by season (descending)
        transfers_by_season_list = sorted(
            transfers_by_season.values(),
            key=lambda x: x['season'],
            reverse=True
        )
        
        cursor.close()
        conn.close()
        
        return render_template("club_details.html", 
                             club=club_data,
                             other_clubs=other_clubs,
                             transfers_by_season=transfers_by_season_list)
        
    except Error as e:
        print(f"Error fetching club details: {e}")
        abort(500, description=f"Database error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        abort(500, description="An unexpected error occurred")
