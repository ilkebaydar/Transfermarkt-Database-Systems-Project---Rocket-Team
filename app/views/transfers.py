from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.db import get_db_connection 
from datetime import datetime
from flask import jsonify
import math 


transfers_bp = Blueprint('transfers', __name__, url_prefix='/transfers')

#Helper func for searching an entity in db, checks exact match and partial match
#returns error if multiple partial matches found to prevent ambiguity
def find_entity(cursor, table, name_input):
    """
    Safely searches for an entity in the database.
    1. Checks for Exact Match.
    2. Counts total partial matches (LIKE) to report accurate numbers.
    3. Returns Error if multiple partial matches found (Ambiguity) or none found.
    """
    # Exact Match 
    query_exact = f"SELECT * FROM {table} WHERE name = %s"
    cursor.execute(query_exact, (name_input,))
    exact_match = cursor.fetchone()

    if exact_match:
        id_col = 'player_id' if table == 'players' else 'club_id'
        return exact_match[id_col], exact_match['name'], exact_match.get('market_value', 0), None

    # Smart Search - Get Real Count 
    count_query = f"SELECT COUNT(*) as total FROM {table} WHERE name LIKE %s"
    cursor.execute(count_query, (f"%{name_input}%",))
    count_result = cursor.fetchone()
    total_matches = count_result['total'] if count_result else 0

    if total_matches == 0:
        return None, None, 0, f"No record found for '{name_input}' in {table}. Please create it first."
    
    elif total_matches == 1:
        # If exactly one match, fetch it
        fetch_query = f"SELECT * FROM {table} WHERE name LIKE %s"
        cursor.execute(fetch_query, (f"%{name_input}%",))
        match = cursor.fetchone()
        
        id_col = 'player_id' if table == 'players' else 'club_id'
        return match[id_col], match['name'], match.get('market_value', 0), None
    
    else:
        #If Ambiguous (>1), fetch 3 examples for display.
        example_query = f"SELECT name FROM {table} WHERE name LIKE %s LIMIT 3"
        cursor.execute(example_query, (f"%{name_input}%",))
        examples = cursor.fetchall()
        
        example_str = ", ".join([m['name'] for m in examples])
        
        return None, None, 0, f"'{name_input}' is ambiguous. Found {total_matches} matches (e.g. {example_str}...). Be specific."

#Helper func is used to unified validation logic for add and update operations
# if manual input exists, it takes precedence. if no manual input checks dropdown ids. 
def resolve_entity(cursor, table, id_input, manual_input):
    """
    Guarantees Safe String Handling.
    Returns: (Name, ID, MarketValue, Error)
    """
    
    # Attribute Error protection
    s_manual = str(manual_input).strip() if manual_input is not None else ""
    s_id = str(id_input).strip() if id_input is not None else ""

    # Conflict Check - both type manually and select from db
    if s_manual and s_id:
        if s_id.isdigit():
            return None, None, 0, f"Please select from the list OR type manually, not both for {table}."

    # 1. Look for Manual Input
    if s_manual:
        fid, fname, fval, err = find_entity(cursor, table, s_manual)
        if err: return None, None, 0, err
        return fname, fid, fval, None # SWAP: Name first

    # 2. Look for ID Input (Dropdown)
    if s_id:
        if not s_id.isdigit():
            fid, fname, fval, err = find_entity(cursor, table, s_id)
            if err: return None, None, 0, err
            return fname, fid, fval, None

        # check via id directly
        pk_col = 'player_id' if table == 'players' else 'club_id'
        query = f"SELECT * FROM {table} WHERE {pk_col} = %s"
        cursor.execute(query, (int(s_id),)) # int() casting is safe here
        res = cursor.fetchone()

        if res:
            # RETURN: Name, ID, Value, None
            return res['name'], res[pk_col], res.get('market_value', 0), None
        else:
            return None, None, 0, f"ID {s_id} not found in {table}."

    return None, None, 0, None


# LISTING PAGE (SELECT Operation)
@transfers_bp.route('/', methods=['GET'])
def index():
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '').strip()
    
    per_page = 20
    offset = (page - 1) * per_page

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error', 'danger')
        return render_template('transfers.html', transfers=[], total_pages=1, current_page=1, total_count=0)
    
    cursor = conn.cursor(dictionary=True)

    # Base SQL parts
    where_clause = ""
    params = []
    
    if search_query:
        where_clause = " WHERE t.player_name LIKE %s"
        params.append(f"%{search_query}%")

    # Count query
    count_query = f"SELECT COUNT(*) as total FROM transfers t {where_clause}"
    cursor.execute(count_query, tuple(params))
    
    result = cursor.fetchone()
    total_count = result['total'] if result else 0
    
    total_pages = (total_count + per_page - 1) // per_page

    # Data Query
    query = f"""
        SELECT t.*, 
               p.country_of_citizenship, 
               p.date_of_birth, 
               p.position,
               p.image_url,
               YEAR(p.date_of_birth) as birth_year
        FROM transfers t
        LEFT JOIN players p ON t.player_id = p.player_id
        {where_clause}
        ORDER BY t.transfer_date DESC
        LIMIT %s OFFSET %s
    """
    
    data_params = params.copy()
    data_params.extend([per_page, offset])
    
    cursor.execute(query, tuple(data_params))
    transfers = cursor.fetchall()
    
    # Fetch Dropdown Data
    cursor.execute("SELECT player_id, name FROM players ORDER BY name")
    players = cursor.fetchall()

    cursor.execute("SELECT club_id, name FROM clubs ORDER BY name")
    clubs = cursor.fetchall()

    cursor.close()
    conn.close()

    # Smart Pagination
    iter_pages = []
    if total_pages <= 7:
        iter_pages = range(1, total_pages + 1)
    else:
        # Always add the first page
        iter_pages.append(1)
        if page > 3: # Left gap
            iter_pages.append(None) 
        # Middle Window (2 pages before and 2 pages after current page)
        start = max(2, page - 2)
        end = min(total_pages - 1, page + 2)
        
        for i in range(start, end + 1):
            iter_pages.append(i)
    
        if page < total_pages - 2: #Right gap
            iter_pages.append(None)
            
        # Always add the last page
        iter_pages.append(total_pages)

    return render_template('transfers.html', 
                           transfers=transfers, 
                           players=players, 
                           clubs=clubs, 
                           total_pages=total_pages, 
                           current_page=page,
                           total_count=total_count,
                           search_query=search_query,
                           iter_pages=iter_pages)

# ADD TRANSFER (INSERT operation)
@transfers_bp.route('/add', methods=['POST'])
def add_transfer():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get data safely: STR conversion prevents 'int' has no strip error
        
        # Player Data
        raw_p_id = request.form.get('player_id')
        player_id_input = str(raw_p_id).strip() if raw_p_id is not None else None
        
        raw_p_manual = request.form.get('player_manual')
        player_manual = str(raw_p_manual).strip() if raw_p_manual is not None else None

        # Clubs Data
        raw_from_id = request.form.get('from_club_id')
        from_club_id = str(raw_from_id).strip() if raw_from_id is not None else None
        
        raw_to_id = request.form.get('to_club_id')
        to_club_id = str(raw_to_id).strip() if raw_to_id is not None else None

        raw_from_manual = request.form.get('from_club_manual')
        from_club_manual = str(raw_from_manual).strip() if raw_from_manual is not None else None

        raw_to_manual = request.form.get('to_club_manual')
        to_club_manual = str(raw_to_manual).strip() if raw_to_manual is not None else None

        # Other Fields
        date = request.form.get('transfer_date')
        season = request.form.get('transfer_season')
        fee = request.form.get('transfer_fee')

        #  Resolve Player
        final_player_name, final_player_id, final_market_value, err = resolve_entity(
            cursor, 'players', player_id_input, player_manual
        )
        if err:
            flash(f"Player Error: {err}", 'danger')
            return redirect(url_for('transfers.index', show_add=1))

        # Resolve From Club
        final_from_name, final_from_id, _, err = resolve_entity(
            cursor, 'clubs', from_club_id, from_club_manual
        )
        if err:
            flash(f"From Club Error: {err}", 'danger')
            return redirect(url_for('transfers.index', show_add=1))

        # Resolve To Club
        final_to_name, final_to_id, _, err = resolve_entity(
            cursor, 'clubs', to_club_id, to_club_manual
        )
        if err:
            flash(f"To Club Error: {err}", 'danger')
            return redirect(url_for('transfers.index', show_add=1))


        # if from club and to club same, it fails
        if final_from_name and final_to_name:
            if final_from_name.strip().lower() == final_to_name.strip().lower():
                flash('Transfer failed: From Club and To Club cannot be the same.', 'danger')
                return redirect(url_for('transfers.index', show_add=1))

        # mandatory check
        missing = []
        if not final_player_name: missing.append("Player")
        if not final_from_name: missing.append("From Club")
        if not final_to_name: missing.append("To Club")
        if not date: missing.append("Date")
        if not fee: missing.append("Fee")

        if missing:
            flash(f"Missing fields: {', '.join(missing)}", 'danger')
            return redirect(url_for('transfers.index', show_add=1))

        if float(fee) < 0:
            flash('Fee must be >= 0', 'danger')
            return redirect(url_for('transfers.index', show_add=1))

        # date format check
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            flash('Invalid Date Format! Use YYYY-MM-DD.', 'danger')
            return redirect(url_for('transfers.index', show_add=1))

        # insert query
        insert_query = """
            INSERT INTO transfers (
                player_id, from_club_id, to_club_id, transfer_date, transfer_season, 
                transfer_fee, market_value_in_eur, 
                player_name, from_club_name, to_club_name
            ) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (final_player_id, final_from_id, final_to_id, date, season, fee, final_market_value,
                  final_player_name, final_from_name, final_to_name)

        cursor.execute(insert_query, values)
        new_transfer_id = cursor.lastrowid

        # Sync: Auto-Update Player's club
        if final_player_id and final_to_id:
            #check tranfer date is new or not
            try:
                transfer_date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                today_date = datetime.now().date()

                if transfer_date_obj >= today_date:
                    cursor.execute("UPDATE players SET current_club_id = %s WHERE player_id = %s", (final_to_id, final_player_id))
                else:
                    print(f"INFO: Player's current club NOT updated because transfer date ({date}) is in the past.")
            except ValueError:
                pass
        conn.commit()
        flash('Transfer added successfully!', 'success')

    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc() 
        flash(f'Database Error: {e}', 'danger')
        print(f"INSERT ERROR: {e}")
        return redirect(url_for('transfers.index', show_add=1))

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('transfers.index'))


#  DELETE TRANSFER (DELETE Operation)

@transfers_bp.route('/delete/<int:transfer_id>', methods=['POST'])
def delete_transfer(transfer_id):
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error', 'danger')
        return redirect(url_for('transfers.index'))
        
    try:
        cursor = conn.cursor()
        query = "DELETE FROM transfers WHERE transfer_id = %s"
        cursor.execute(query, (transfer_id,))
        conn.commit()
        
        flash('Transfer deleted successfully.', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting transfer: {e}', 'danger')
        print(f"DELETE ERROR: {e}")
        
    finally:
        if conn and cursor:
            cursor.close()
            conn.close()
            
    return redirect(url_for('transfers.index'))

#TRANSFER UPDATE 
@transfers_bp.route('/edit/<int:transfer_id>', methods=['GET', 'POST'])
def edit_transfer(transfer_id):
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error', 'danger')
        return redirect(url_for('transfers.index'))
    
    try:
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        return f"Database Cursor Error: {e}"

    # Get Request
    if request.method == 'GET':
        cursor.execute("SELECT * FROM transfers WHERE transfer_id = %s", (transfer_id,))
        transfer = cursor.fetchone()

        if not transfer:
            flash('Transfer not found!', 'danger')
            return redirect(url_for('transfers.index'))

        player_image = None
        if transfer.get('player_id'):
            cursor.execute("SELECT image_url FROM players WHERE player_id = %s", (transfer['player_id'],))
            player_data = cursor.fetchone()
            if player_data:
                player_image = player_data['image_url']

        cursor.execute("SELECT club_id, name FROM clubs ORDER BY name")
        clubs = cursor.fetchall()

        conn.close()
        return render_template('edit_transfer.html', transfer=transfer, clubs=clubs, player_image=player_image)

    # Post Request
    elif request.method == 'POST':
        try:
          # Player ID
            raw_p_id = request.form.get('player_id')
            player_id = str(raw_p_id).strip() if raw_p_id is not None else None

            # From Club Data
            raw_from_id = request.form.get('from_club_id')
            from_club_id = str(raw_from_id).strip() if raw_from_id is not None else None
            
            raw_from_manual = request.form.get('from_club_manual')
            from_club_manual = str(raw_from_manual).strip() if raw_from_manual is not None else None

            # To Club Data
            raw_to_id = request.form.get('to_club_id')
            to_club_id = str(raw_to_id).strip() if raw_to_id is not None else None
            
            raw_to_manual = request.form.get('to_club_manual')
            to_club_manual = str(raw_to_manual).strip() if raw_to_manual is not None else None

            date = request.form.get('transfer_date')
            season = request.form.get('transfer_season')
            fee = request.form.get('transfer_fee')

            
            # Resolve- from club
            final_from_name, final_from_id, _, err = resolve_entity(cursor, 'clubs', from_club_id, from_club_manual)
            if err:
                flash(f"From Club Error: {err}", 'danger')
                return redirect(url_for('transfers.edit_transfer', transfer_id=transfer_id)) 

            #Resolve- to club
            final_to_name, final_to_id, _, err = resolve_entity(cursor, 'clubs', to_club_id, to_club_manual)
            if err:
                flash(f"To Club Error: {err}", 'danger')
                return redirect(url_for('transfers.edit_transfer', transfer_id=transfer_id))
            #ıf from club and to club same, it gives fail
            if final_from_id and final_to_id:
                if final_from_id == final_to_id:
                    flash('Update failed: From Club and To Club cannot be the same.', 'warning')
                    return redirect(url_for('transfers.edit_transfer', transfer_id=transfer_id))
            
            # If club name written manually, check it
            elif final_from_name and final_to_name:
                if final_from_name.strip().lower() == final_to_name.strip().lower():
                    flash('Update failed: From Club and To Club cannot be the same.', 'warning')
                    return redirect(url_for('transfers.edit_transfer', transfer_id=transfer_id))

            # Update query
            update_query = """
                UPDATE transfers SET
                    from_club_id=%s, to_club_id=%s,
                    transfer_date=%s, transfer_season=%s, transfer_fee=%s,
                    from_club_name=%s, to_club_name=%s
                WHERE transfer_id=%s
            """
            values = (
                final_from_id, final_to_id,
                date, season, fee,
                final_from_name, final_to_name,
                transfer_id
            )
            
            cursor.execute(update_query, values)

            #Syncronization
            #find which player belongs to this transfer
            cursor.execute("SELECT player_id FROM transfers WHERE transfer_id = %s", (transfer_id,))
            t_record = cursor.fetchone()

           # If player ID and the new club ID is valid, update the player's profile
            if t_record and t_record['player_id'] and final_to_id:
                target_player_id = t_record['player_id']
                try:
                    transfer_date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                    today_date = datetime.now().date()
                #check transfer date, if it is new update else do nothing
                    if transfer_date_obj >= today_date:
                        cursor.execute("""
                            UPDATE players 
                            SET current_club_id = %s 
                            WHERE player_id = %s
                        """, (final_to_id, target_player_id))
                    else:
                        print(f"INFO: Player's current club NOT updated because transfer date ({date}) is in the past.")

                except ValueError:
                    print(f"ERROR: Date parsing failed for {date}")

            conn.commit()
            
            flash('Transfer updated successfully!', 'success')
            return redirect(url_for('transfers.index'))

        except Exception as e:
            conn.rollback()
            flash(f"Error updating transfer: {e}", 'danger')
            return redirect(url_for('transfers.edit_transfer', transfer_id=transfer_id))

        finally:
            if conn and cursor:
                cursor.close()
                conn.close()

#AUTOCOMPLETE API 
@transfers_bp.route('/autocomplete', methods=['GET'])
def autocomplete():
    term = request.args.get('term', '').strip()

    if len(term) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    if conn is None:
        return jsonify([])
    
    cursor = conn.cursor(dictionary= True)

    #first check string, if exists git it priority 0(on top) if no priority 1.
    #then sort alphabetically
    query = """
        SELECT name FROM players 
        WHERE name LIKE %s 
        ORDER BY 
            CASE WHEN name LIKE %s THEN 0 ELSE 1 END, 
            name ASC 
        LIMIT 10
    """
    #first term for searching anywhere in name, second term for checkin if it starts with term(for sorting)
    cursor.execute(query, (f"%{term}%", f"{term}%"))
    results = cursor.fetchall()

    conn.close()

    suggestions = [row['name'] for row in results]

    return jsonify(suggestions)


#This func for financial statistics about transfers
@transfers_bp.route('/stats')
def transfer_stats():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Stat: Latest 50 Transfers with Value Difference
    stats_query = """
        SELECT 
            t.transfer_id,
            t.player_name,
            p.image_url,
            t.to_club_name,
            t.transfer_fee,
            t.transfer_date,
            p.market_value,
            (p.market_value - t.transfer_fee) as value_diff
        FROM transfers t
        JOIN players p ON t.player_id = p.player_id
        WHERE t.transfer_fee > 0 AND p.market_value > 0
        ORDER BY t.transfer_date DESC
        LIMIT 50
    """
    cursor.execute(stats_query)
    stats_data = cursor.fetchall()

    # 2. Stat: Top 10 Clubs by Total Spending
    # Replaces the chart area with a financial summary table
    spenders_query = """
        SELECT 
            to_club_name, 
            SUM(transfer_fee) as total_spent, 
            COUNT(*) as transfer_count
        FROM transfers
        WHERE transfer_fee > 0
        GROUP BY to_club_name
        ORDER BY total_spent DESC
        LIMIT 10
    """

   # 3. Complex Stat: "High Roller Clubs"
    # Logic: Find clubs whose total spending is significant relative to the average.
    # Multiplied average by 0.2 to include more clubs since top clubs skew the average too high.
    complex_stats_query = """
        SELECT 
            t.to_club_name, 
            SUM(t.transfer_fee) as total_spent,
            COUNT(*) as transfer_count
        FROM transfers t
        WHERE t.transfer_fee > 0
        GROUP BY t.to_club_name
        HAVING total_spent > (
            SELECT AVG(club_total) * 0.2 
            FROM (
                SELECT SUM(transfer_fee) as club_total 
                FROM transfers 
                WHERE transfer_fee > 0 
                GROUP BY to_club_name
            ) as subquery_table
        )
        ORDER BY total_spent DESC
        LIMIT 5
    """
    cursor.execute(complex_stats_query)
    high_rollers = cursor.fetchall()

    cursor.execute(spenders_query)
    top_spenders = cursor.fetchall()

    conn.close()
    
    return render_template(
        'transfer_stats.html', 
        stats=stats_data, 
        top_spenders=top_spenders,
        high_rollers=high_rollers
    )