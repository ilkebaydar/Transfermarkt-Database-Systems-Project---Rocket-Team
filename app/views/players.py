from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.db import get_db_connection
from mysql.connector import Error

# Blueprint Definition
players_bp = Blueprint('players', __name__, url_prefix='/players')


# LISTING PAGE
@players_bp.route('/')
def index():
    return render_template('players.html')


# API: Get all players
@players_bp.route('/api/players', methods=['GET'])
def get_players():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get search query parameter
        search_query = request.args.get('search', '').strip()
        
        # Get filter parameters
        filter_position = request.args.get('position', '').strip()
        filter_sub_position = request.args.get('sub_position', '').strip()
        filter_country = request.args.get('country', '').strip()
        filter_club_id = request.args.get('club_id', '').strip()
        filter_foot = request.args.get('foot', '').strip()
        filter_min_age = request.args.get('min_age', '').strip()
        filter_max_age = request.args.get('max_age', '').strip()
        
        # Get sorting parameters
        order_by = request.args.get('order_by', 'name').strip()
        order_direction = request.args.get('order_direction', 'asc').strip().upper()
        
        # Validate order_by to prevent SQL injection
        allowed_order_by = ['name', 'market_value', 'date_of_birth', 'age', 'position', 'country_of_citizenship', 'club_name']
        if order_by not in allowed_order_by:
            order_by = 'name'
        
        # Validate order_direction
        if order_direction not in ['ASC', 'DESC']:
            order_direction = 'ASC'
        
        # Map order_by to actual column names or expressions
        order_by_map = {
            'name': 'p.name',
            'market_value': 'p.market_value',
            'date_of_birth': 'p.date_of_birth',
            'age': 'TIMESTAMPDIFF(YEAR, p.date_of_birth, CURDATE())',  # Calculate age
            'position': 'p.position',
            'country_of_citizenship': 'p.country_of_citizenship',
            'club_name': 'c.name'
        }
        order_by_column = order_by_map.get(order_by, 'p.name')
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))  # 50 players per page
        offset = (page - 1) * per_page
        
        # Base query
        base_query = """
            SELECT 
                p.player_id,
                p.name,
                p.current_club_id,
                c.name AS club_name,
                p.last_season,
                p.country_of_citizenship,
                p.date_of_birth,
                p.position,
                p.sub_position,
                p.foot,
                p.market_value,
                p.image_url
            FROM Players p
            LEFT JOIN Clubs c ON p.current_club_id = c.club_id
        """
        
        # Count query for total records
        count_query = "SELECT COUNT(*) as total FROM Players p LEFT JOIN Clubs c ON p.current_club_id = c.club_id"
        
        # Build WHERE clause with filters
        where_conditions = []
        params = []
        
        # Search query (OR conditions)
        if search_query:
            search_pattern = f"%{search_query}%"
            where_conditions.append("""
                (p.name LIKE %s 
                   OR p.position LIKE %s 
                   OR p.country_of_citizenship LIKE %s
                   OR c.name LIKE %s)
            """)
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
        
        # Filter conditions (AND conditions)
        if filter_position:
            where_conditions.append("p.position = %s")
            params.append(filter_position)
        
        if filter_sub_position:
            where_conditions.append("p.sub_position = %s")
            params.append(filter_sub_position)
        
        if filter_country:
            where_conditions.append("p.country_of_citizenship = %s")
            params.append(filter_country)
        
        if filter_club_id:
            try:
                club_id_int = int(filter_club_id)
                where_conditions.append("p.current_club_id = %s")
                params.append(club_id_int)
            except ValueError:
                pass
        
        if filter_foot:
            where_conditions.append("p.foot = %s")
            params.append(filter_foot)
        
        # Age range filters
        if filter_min_age:
            try:
                min_age_int = int(filter_min_age)
                where_conditions.append("TIMESTAMPDIFF(YEAR, p.date_of_birth, CURDATE()) >= %s")
                params.append(min_age_int)
            except ValueError:
                pass
        
        if filter_max_age:
            try:
                max_age_int = int(filter_max_age)
                where_conditions.append("TIMESTAMPDIFF(YEAR, p.date_of_birth, CURDATE()) <= %s")
                params.append(max_age_int)
            except ValueError:
                pass
        
        # Combine WHERE conditions
        where_clause = ""
        if where_conditions:
            where_clause = " WHERE " + " AND ".join(where_conditions)
        
        # Get total count
        count_query_with_where = count_query + where_clause
        if where_clause:
            cursor.execute(count_query_with_where, params)
        else:
            cursor.execute(count_query)
        total_count = cursor.fetchone()['total']
        total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
        
        # Get paginated data with sorting
        # Note: order_by_column is already validated against whitelist, so safe to use in f-string
        query = base_query + where_clause + f" ORDER BY {order_by_column} {order_direction} LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        cursor.execute(query, params)
        players = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'players': players,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'total_pages': total_pages
            }
        })
    except Error as e:
        print(f"Error fetching players: {e}")
        return jsonify({"error": "Failed to retrieve players"}), 500


# API: Get clubs for dropdown
@players_bp.route('/api/clubs', methods=['GET'])
def get_clubs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT club_id, name FROM Clubs ORDER BY name")
        clubs = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(clubs)
    except Error as e:
        print(f"Error fetching clubs: {e}")
        return jsonify({"error": "Failed to retrieve clubs"}), 500


# API: Get distinct filter values
@players_bp.route('/api/filters', methods=['GET'])
def get_filter_values():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get distinct positions
        cursor.execute("SELECT DISTINCT position FROM Players WHERE position IS NOT NULL AND position != '' ORDER BY position")
        positions = [row['position'] for row in cursor.fetchall()]
        
        # Get distinct sub_positions
        cursor.execute("SELECT DISTINCT sub_position FROM Players WHERE sub_position IS NOT NULL AND sub_position != '' ORDER BY sub_position")
        sub_positions = [row['sub_position'] for row in cursor.fetchall()]
        
        # Get distinct countries
        cursor.execute("SELECT DISTINCT country_of_citizenship FROM Players WHERE country_of_citizenship IS NOT NULL AND country_of_citizenship != '' ORDER BY country_of_citizenship")
        countries = [row['country_of_citizenship'] for row in cursor.fetchall()]
        
        # Get distinct foot values
        cursor.execute("SELECT DISTINCT foot FROM Players WHERE foot IS NOT NULL AND foot != '' ORDER BY foot")
        feet = [row['foot'] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'positions': positions,
            'sub_positions': sub_positions,
            'countries': countries,
            'feet': feet
        })
    except Error as e:
        print(f"Error fetching filter values: {e}")
        return jsonify({"error": "Failed to retrieve filter values"}), 500


# API: Get sub_positions filtered by position
@players_bp.route('/api/sub-positions', methods=['GET'])
def get_sub_positions_by_position():
    try:
        position = request.args.get('position', '').strip()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if position:
            # Get distinct sub_positions for the selected position
            cursor.execute(
                "SELECT DISTINCT sub_position FROM Players WHERE position = %s AND sub_position IS NOT NULL AND sub_position != '' ORDER BY sub_position",
                (position,)
            )
        else:
            # If no position selected, return all sub_positions
            cursor.execute("SELECT DISTINCT sub_position FROM Players WHERE sub_position IS NOT NULL AND sub_position != '' ORDER BY sub_position")
        
        sub_positions = [row['sub_position'] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({'sub_positions': sub_positions})
    except Error as e:
        print(f"Error fetching sub_positions: {e}")
        return jsonify({"error": "Failed to retrieve sub_positions"}), 500


# API: Add new player
@players_bp.route('/api/players/add', methods=['POST'])
def add_player():
    data = request.get_json()
    
    name = data.get('name')
    current_club_id = data.get('current_club_id') if data.get('current_club_id') else None
    last_season = data.get('last_season') if data.get('last_season') else None
    country_of_citizenship = data.get('country_of_citizenship')
    date_of_birth = data.get('date_of_birth') if data.get('date_of_birth') else None
    position = data.get('position')
    sub_position = data.get('sub_position')
    foot = data.get('foot')
    market_value = data.get('market_value') if data.get('market_value') else None
    image_url = data.get('image_url')

    # Basic validation
    if not name:
        return jsonify({"error": "Player name is required"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO Players (
                name, current_club_id, last_season, country_of_citizenship,
                date_of_birth, position, sub_position, foot, market_value, image_url
            ) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            name,
            current_club_id if current_club_id else None,
            int(last_season) if last_season else None,
            country_of_citizenship if country_of_citizenship else None,
            date_of_birth if date_of_birth else None,
            position if position else None,
            sub_position if sub_position else None,
            foot if foot else None,
            float(market_value) if market_value else None,
            image_url if image_url else None
        )
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Player added successfully"})
    except Error as e:
        print(f"Error adding player: {e}")
        return jsonify({"error": str(e)}), 500


# PLAYER DETAIL PAGE
@players_bp.route('/<int:player_id>')
def player_detail(player_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Basic player info query (with club average age and competition_id)
        query = """
            SELECT 
                p.player_id,
                p.name,
                p.current_club_id,
                c.name AS club_name,
                c.average_age AS club_average_age,
                c.competition_id AS club_competition_id,
                p.last_season,
                p.country_of_citizenship,
                p.date_of_birth,
                p.position,
                p.sub_position,
                p.foot,
                p.market_value,
                p.image_url
            FROM players p
            LEFT JOIN clubs c ON p.current_club_id = c.club_id
            WHERE p.player_id = %s
        """
        cursor.execute(query, (player_id,))
        player = cursor.fetchone()
        
        if not player:
            cursor.close()
            conn.close()
            return render_template('player_detail.html', player=None, error="Player not found")
        
        # Calculate player age
        player_age = None
        if player.get('date_of_birth'):
            age_query = "SELECT TIMESTAMPDIFF(YEAR, %s, CURDATE()) AS age"
            cursor.execute(age_query, (player['date_of_birth'],))
            age_result = cursor.fetchone()
            if age_result:
                player_age = age_result['age']
        
        # Check if player is active
        is_active = player.get('last_season') is not None and player.get('last_season') >= 2023
        
        # Determine player status message
        player_status = None
        if not is_active:
            if player.get('current_club_id'):
                player_status = "This player is not active or in a non-European team."
            else:
                player_status = "This player is not currently active."
        
        # Initialize comparison stats
        club_age_stats = {
            'player_age': player_age,
            'club_average_age': player.get('club_average_age'),
            'club_age_difference': None,
            'league_average_age': None,
            'league_age_difference': None,
            'club_average_market_value': None,
            'league_average_market_value': None,
            'club_mv_difference': None,
            'league_mv_difference': None,
            'is_active': is_active,
            'status_message': player_status
        }
        
        # Calculate age differences
        if player_age is not None and player.get('club_average_age') is not None:
            club_age_stats['club_age_difference'] = round(player_age - player['club_average_age'], 1)
        
        # Calculate league average age (weighted average)
        if player.get('club_competition_id'):
            try:
                league_age_query = """
                    SELECT
                        SUM(c2.average_age * c2.squad_size) / SUM(c2.squad_size) AS league_avg_age
                    FROM clubs c2
                    WHERE c2.competition_id = %s
                        AND c2.average_age IS NOT NULL
                        AND c2.squad_size > 0
                """
                cursor.execute(league_age_query, (player['club_competition_id'],))
                league_age_result = cursor.fetchone()
                if league_age_result and league_age_result.get('league_avg_age'):
                    club_age_stats['league_average_age'] = float(league_age_result['league_avg_age'])
                    if player_age is not None:
                        club_age_stats['league_age_difference'] = round(player_age - club_age_stats['league_average_age'], 1)
            except Error as e:
                print(f"Error fetching league average age: {e}")
        
        # Calculate club average market value (active players only)
        if player.get('current_club_id'):
            try:
                club_mv_query = """
                    SELECT AVG(market_value) AS club_avg_mv
                    FROM players
                    WHERE current_club_id = %s
                        AND market_value IS NOT NULL
                        AND last_season >= 2023
                """
                cursor.execute(club_mv_query, (player['current_club_id'],))
                club_mv_result = cursor.fetchone()
                if club_mv_result and club_mv_result.get('club_avg_mv'):
                    club_age_stats['club_average_market_value'] = float(club_mv_result['club_avg_mv'])
                    if player.get('market_value') is not None:
                        club_age_stats['club_mv_difference'] = player['market_value'] - club_age_stats['club_average_market_value']
            except Error as e:
                print(f"Error fetching club average market value: {e}")
        
        # Calculate league average market value (active players only)
        if player.get('club_competition_id'):
            try:
                league_mv_query = """
                    SELECT AVG(p2.market_value) AS league_avg_mv
                    FROM players p2
                    INNER JOIN clubs c2 ON p2.current_club_id = c2.club_id
                    WHERE c2.competition_id = %s
                        AND p2.market_value IS NOT NULL
                        AND p2.last_season >= 2023
                """
                cursor.execute(league_mv_query, (player['club_competition_id'],))
                league_mv_result = cursor.fetchone()
                if league_mv_result and league_mv_result.get('league_avg_mv'):
                    club_age_stats['league_average_market_value'] = float(league_mv_result['league_avg_mv'])
                    if player.get('market_value') is not None:
                        club_age_stats['league_mv_difference'] = player['market_value'] - club_age_stats['league_average_market_value']
            except Error as e:
                print(f"Error fetching league average market value: {e}")
        
        # Transfer History Query
        try:
            # Get player name for matching
            player_name = player.get('name', '')
            
            # Simple query - directly from transfers table
            transfer_history_query = """
                SELECT 
                    t.transfer_id,
                    t.transfer_date,
                    t.transfer_season,
                    t.transfer_fee,
                    t.market_value_in_eur,
                    t.from_club_name,
                    t.to_club_name,
                    t.from_club_id,
                    t.to_club_id,
                    t.player_name
                FROM transfers t
                WHERE t.player_id = %s OR t.player_name LIKE %s
                ORDER BY 
                    COALESCE(t.transfer_date, '1900-01-01') DESC,
                    t.transfer_season DESC
            """
            cursor.execute(transfer_history_query, (player_id, f"%{player_name}%"))
            transfer_history = cursor.fetchall()
        except Error as e:
            print(f"Error fetching transfer history: {e}")
            import traceback
            traceback.print_exc()
            transfer_history = []
        
        cursor.close()
        conn.close()
        
        return render_template('player_detail.html', 
                            player=player, 
                            transfer_history=transfer_history,
                            club_age_stats=club_age_stats)
    except Error as e:
        print(f"Error fetching player: {e}")
        import traceback
        traceback.print_exc()
        return render_template('player_detail.html', player=None, error=f"Failed to retrieve player: {str(e)}")


# API: Get single player (for edit form)
@players_bp.route('/api/players/<int:player_id>', methods=['GET'])
def get_player(player_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Players WHERE player_id = %s", (player_id,))
        player = cursor.fetchone()
        cursor.close()
        conn.close()
        if player:
            return jsonify(player)
        else:
            return jsonify({"error": "Player not found"}), 404
    except Error as e:
        print(f"Error fetching player: {e}")
        return jsonify({"error": "Failed to retrieve player"}), 500


# API: Update player
@players_bp.route('/api/players/update/<int:player_id>', methods=['PUT'])
def update_player(player_id):
    data = request.get_json()
    
    # Only get editable fields
    last_season = data.get('last_season') if data.get('last_season') else None
    position = data.get('position')
    sub_position = data.get('sub_position')
    foot = data.get('foot')
    market_value = data.get('market_value') if data.get('market_value') else None
    image_url = data.get('image_url')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            UPDATE players SET
                last_season = %s,
                position = %s,
                sub_position = %s,
                foot = %s,
                market_value = %s,
                image_url = %s
            WHERE player_id = %s
        """
        values = (
            int(last_season) if last_season else None,
            position if position else None,
            sub_position if sub_position else None,
            foot if foot else None,
            float(market_value) if market_value else None,
            image_url if image_url else None,
            player_id
        )
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Player updated successfully"})
    except Error as e:
        print(f"Error updating player: {e}")
        return jsonify({"error": str(e)}), 500


# API: Delete player
@players_bp.route('/api/players/delete/<int:player_id>', methods=['DELETE'])
def delete_player(player_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Players WHERE player_id = %s", (player_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Player deleted successfully"})
    except Error as e:
        print(f"Error deleting player: {e}")
        return jsonify({"error": str(e)}), 500