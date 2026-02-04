/* -------------------------------------------------------------------------
   IMPORTANT NOTE FOR TEAM:
   1. You must replace 'YOUR_ABSOLUTE_PATH_TO_PROJECT' with your actual file path.
   
   2. PATH FORMATTING WARNING (Especially for Windows Users):
      If you copy the path directly, it will look like:
      'C:\Users\Name\Desktop\...'
      
      You MUST replace backslashes (\) with forward slashes (/).
      
   -------------------------------------------------------------------------
*/

-- Enable local file loading on the server side
SET GLOBAL local_infile = 1;

-- Disable foreign key checks to prevent errors during bulk data import
SET FOREIGN_KEY_CHECKS = 0;

-- Import Data: Clubs

-- CSV: club_id, club_code, name, domestic_competition_id, total_market_value, squad_size, 
-- average_age, foreigners_number, foreigners_percentage, national_team_players, 
-- stadium_name, stadium_seats, net_transfer_record, coach_name, last_season, filename, url
LOAD DATA LOCAL INFILE 'YOUR_ABSOLUTE_PATH_TO_PROJECT/db/csv files/clubs.csv'
INTO TABLE Clubs
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    club_id, 
    club_code, 
    name, 
    competition_id, 
    @dummy,         -- total_market_value (skip)
    squad_size, 
    average_age, 
    @dummy,         -- foreigners_number (skip)
    @dummy,         -- foreigners_percentage (skip)
    @dummy,         -- national_team_players (skip)
    stadium_name, 
    stadium_seats, 
    @dummy,         -- net_transfer_record (skip)
    @dummy,         -- coach_name (skip)
    @dummy,         -- last_season (skip)
    @dummy,         -- filename (skip)
    url
);


-- Import Data: Competitions

-- CSV: competition_id, competition_code, name, sub_type, type, country_id, 
-- country_name, domestic_league_code, confederation, url, is_major_national_league
LOAD DATA LOCAL INFILE 'YOUR_ABSOLUTE_PATH_TO_PROJECT/db/csv files/competitions.csv'
INTO TABLE Competitions
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    competition_id,
    @dummy,               -- competition_code (skip)
    competition_name,     
    competition_sub_type, 
    competition_type,     
    @dummy,               -- country_id (skip)
    country_name,
    @dummy,               -- domestic_league_code (skip)
    @dummy,               -- confederation (skip)
    @dummy,               -- url (skip)
    @dummy                -- is_major_national_league (skip)
);


-- Import Data: Players
-- CSV: player_id, first_name, last_name, name, last_season, current_club_id, player_code, 
-- country_of_birth, city_of_birth, country_of_citizenship, date_of_birth, sub_position, 
-- position, foot, height_in_cm, contract_expiration_date, agent_name, image_url, url, 
-- current_club_domestic_competition_id, current_club_name, market_value_in_eur, highest_market_value_in_eur
LOAD DATA LOCAL INFILE 'YOUR_ABSOLUTE_PATH_TO_PROJECT/db/csv files/players.csv'
INTO TABLE Players
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    player_id,
    @dummy, -- first_name (skip)
    @dummy, -- last_name (skip)
    name,
    last_season,
    current_club_id,
    @dummy, -- player_code (skip)
    @dummy, -- country_of_birth (skip)
    @dummy, -- city_of_birth (skip)
    country_of_citizenship,
    date_of_birth,
    sub_position,
    position,
    foot,
    @dummy, -- height_in_cm (skip)
    @dummy, -- contract_expiration_date (skip)
    @dummy, -- agent_name (skip)
    image_url,
    @dummy, -- url (skip)
    @dummy, -- current_club_domestic_competition_id (skip)
    @dummy, -- current_club_name (skip)
    market_value, 
    @dummy  -- highest_market_value_in_eur (skip)
);


-- Import Data: Games

-- CSV: game_id, competition_id, season, round, date, home_club_id, away_club_id, 
-- home_club_goals, away_club_goals, home_club_position, away_club_position, 
-- home_club_manager_name, away_club_manager_name, stadium, attendance, referee, 
-- url, home_club_formation, away_club_formation, home_club_name, away_club_name, aggregate, competition_type
LOAD DATA LOCAL INFILE 'YOUR_ABSOLUTE_PATH_TO_PROJECT/db/csv files/games.csv'
INTO TABLE Games
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    game_id,
    competition_id,
    season,
    @dummy, -- round (skip)
    date,
    home_club_id,
    away_club_id,
    home_club_goals,
    away_club_goals,
    @dummy, -- home_club_position (skip)
    @dummy, -- away_club_position (skip)
    @dummy, -- home_club_manager_name (skip)
    @dummy, -- away_club_manager_name (skip)
    stadium,
    attendance,
    @dummy, -- referee (skip)
    @dummy, -- url (skip)
    @dummy, -- home_club_formation (skip)
    @dummy, -- away_club_formation (skip)
    @dummy, -- home_club_name (skip)
    @dummy, -- away_club_name (skip)
    @dummy, -- aggregate (skip)
    @dummy  -- competition_type (skip)
);


-- Import Data: Transfers
-- CSV: player_id, transfer_date, transfer_season, from_club_id, to_club_id, 
-- from_club_name, to_club_name, transfer_fee, market_value_in_eur, player_name
LOAD DATA LOCAL INFILE 'YOUR_ABSOLUTE_PATH_TO_PROJECT/db/csv files/transfers.csv'
INTO TABLE Transfers
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    player_id,
    transfer_date,
    transfer_season,
    from_club_id,
    to_club_id,
    from_club_name,
    to_club_name,
    transfer_fee,
    market_value_in_eur,
    player_name
);

-- Re-enable foreign key checks to maintain data integrity
SET FOREIGN_KEY_CHECKS = 1;

-- Normalize country names: Turkey -> Türkiye
SET SQL_SAFE_UPDATES = 0;

UPDATE Players 
SET country_of_citizenship = 'Türkiye' 
WHERE country_of_citizenship = 'Turkey';

SET SQL_SAFE_UPDATES = 1;

-- Confirm status
SHOW VARIABLES LIKE 'foreign_key_checks';
