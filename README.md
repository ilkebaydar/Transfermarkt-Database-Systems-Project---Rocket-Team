# BLG317E - Rocket Team

BLG317E Database Systems Term Project – Football Transfermarkt dataset implemented using Flask and MySQL.

## Team Members
- İlke Başak Baydar – Transfers
- Onat Barış Ercan – Players
- Furkan Kural – Clubs
- Mustafa Çağşak – Games

## Dataset
Football Transfermarkt  
https://www.kaggle.com/datasets/davidcariboo/player-scores


## NOTES: About Data Insertion
After creating the database schema, use one of the following methods to insert the data:
1. Method: Using insertion query (Recommended)
    You can execute the provided SQL script using a tool like MySQL Workbench or DBeaver.
    File: insert_data_from_csv_to_db.sql 

2. Method: Using Python Script 
    Run the following python script to automatically load data from CSV files into the database:
    python load_tables_from_csv.py
