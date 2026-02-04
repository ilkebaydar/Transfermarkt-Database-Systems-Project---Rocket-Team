CREATE DATABASE IF NOT EXISTS TRANSFERMARKT;
USE TRANSFERMARKT;


CREATE TABLE Clubs (
	club_id INT PRIMARY KEY,
    club_code VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    squad_size INT DEFAULT 0,
    average_age FLOAT,
    stadium_name VARCHAR(255),
    stadium_seats INT,
    url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE Players (
    player_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    current_club_id INT,
    last_season INT,
    country_of_citizenship VARCHAR(50),
    date_of_birth DATE,
    position VARCHAR(50),
    sub_position VARCHAR(50),
    foot VARCHAR(10),
    market_value FLOAT,
    image_url VARCHAR(500),

    CONSTRAINT fk_players_current_club FOREIGN KEY (current_club_id)
        REFERENCES Clubs(club_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE Competitions (
    competition_id VARCHAR(10) PRIMARY KEY,
    competition_name VARCHAR(20),
    competition_sub_type VARCHAR(20),
    competition_type VARCHAR(20),
    country_name VARCHAR(10)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE Games (
    game_id INT PRIMARY KEY AUTO_INCREMENT,
    home_club_id INT,
    away_club_id INT,
    season INT,
    date DATE,
    home_club_goals INT,
    away_club_goals INT,
    stadium VARCHAR(100),
    attendance INT,
    competition_id VARCHAR(10),
    
    CONSTRAINT fk_games_competition_id FOREIGN KEY (competition_id) 
    REFERENCES Competitions(competition_id)
    ON DELETE CASCADE 
    ON UPDATE CASCADE,

    CONSTRAINT fk_games_home_club FOREIGN KEY (home_club_id) 
    REFERENCES Clubs(club_id)
    ON DELETE CASCADE 
    ON UPDATE CASCADE,
    
    CONSTRAINT fk_games_away_club FOREIGN KEY (away_club_id) 
    REFERENCES Clubs(club_id)
    ON DELETE CASCADE 
    ON UPDATE CASCADE

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE Transfers (
    transfer_id INT AUTO_INCREMENT PRIMARY KEY,
    player_id INT,
	transfer_date DATE,
	transfer_season VARCHAR(50) NOT NULL,
    from_club_id INT,
    to_club_id INT,
    from_club_name VARCHAR(100),  
    to_club_name VARCHAR(100),    
    transfer_fee FLOAT,
    market_value_in_eur FLOAT,
    player_name VARCHAR(100) NOT NULL,
    
    CONSTRAINT fk_transfers_player FOREIGN KEY (player_id) 
    REFERENCES Players(player_id)
    ON DELETE CASCADE 
    ON UPDATE CASCADE,
    
    CONSTRAINT fk_transfers_from_club FOREIGN KEY (from_club_id) 
    REFERENCES Clubs(club_id)
    ON DELETE SET NULL 
    ON UPDATE CASCADE,
    
    CONSTRAINT fk_transfers_to_club FOREIGN KEY (to_club_id) 
    REFERENCES Clubs(club_id)
    ON DELETE SET NULL 
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- Sets engine to InnoDB for Foreign Key support 
-- charset to utf8mb4 for special characters.

-- Alter Clubs table with foreign key from Competitions table
ALTER TABLE Clubs 
ADD COLUMN competition_id VARCHAR(10),
ADD CONSTRAINT fk_clubs_competition 
    FOREIGN KEY (competition_id) 
    REFERENCES Competitions(competition_id)
    ON DELETE SET NULL 
    ON UPDATE CASCADE;
