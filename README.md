# Transfermarkt Database Systems Project - Rocket Team

This repository contains the full implementation, database design, and documentation for the **Football Transfermarkt** database project. The project involves a comprehensive SQL-based system designed to manage and analyze football transfers, player statistics, club data, and match results.

## 🎓 Academic Context

This project was developed as the final term project for the **BLG 317E - Database Systems** course at **Istanbul Technical University (ITU)**, Faculty of Computer and Informatics.

* **Term:** Fall 2025
* **Team Name:** Rocket Team

## 👥 Rocket Team Members & Responsibilities

The project responsibilities were distributed among team members based on specific database entities:

* **İlke Başak Baydar (150140709)** – Transfers
* **Onat Barış Ercan (150210075)** – Players
* **Furkan Kural (150210056)** – Clubs
* **Mustafa Çağşak (150220060)** – Games

## 🚀 Project Goal

The Transfermarkt project aims to provide a platform that displays various statistics relating to matches, players, clubs, and transfers. Using a dataset derived from the original website, it offers open access and full management capabilities for all football-related data.

## 🛠️ Technology Stack

Transfermarkt is built using the following core technologies:

* **Database Management System (DBMS):** **MySQL** was selected for its dependability. Specifically, the **InnoDB** storage engine was utilized to ensure data integrity and name consistency across different languages.
* **Backend:** Developed using **Python** and the **Flask** web framework.
* **Frontend:**
    * **HTML5** for structural layout.
    * **Bootstrap 5** as the CSS framework for a responsive and consistent UI.
    * **Jinja2** for server-side template rendering.
    * **jQuery & jQuery UI** for dynamic client-side operations.
    * **Choices.js** for user-friendly dropdown menus.
    * **SweetAlert2** for modern and intuitive alert boxes.

## 📊 Dataset

The project utilizes an extensive football dataset containing historical records of transfers, player performance, and club details.
* **Source:** [Kaggle - Football Player Scores Dataset](https://www.kaggle.com/datasets/davidcariboo/player-scores)

## 📂 Project Structure

The project is organized as follows:

BLG317E-rocketteam/
├── app/                        # Flask application logic
│   ├── static/                 # Images and assets
│   ├── templates/              # HTML files (index, players, clubs, etc.)
│   └── views/                  # Python route definitions (transfers, games, etc.)
├── db/                         # Database scripts
│   ├── transfermarkt_schema.sql # DDL: Table creations and schema
│   └── insert_data_from_csv_to_db.sql # DML: Data insertion queries
├── load_tables_from_csv.py      # Python script for automatic data loading
├── config.py                   # Configuration settings
├── run.py                      # Application entry point
├── requirements.txt            # Necessary Python libraries
├── ProjectReport-RocketTeam.pdf # Detailed technical project report


## 📝 Notes: About Data Insertion

After creating the database schema, use one of the following methods to insert the data:

### Method 1: Using Insertion Query (Recommended)
You can execute the provided SQL script using a tool like MySQL Workbench or DBeaver.
* **File:** `insert_data_from_csv_to_db.sql`

### Method 2: Using Python Script
Run the following python script to automatically load data from CSV files into the database:
```bash
python load_tables_from_csv.py
