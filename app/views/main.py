from flask import Blueprint, jsonify, render_template
from mysql.connector import Error
from app.db import get_db_connection

bp = Blueprint('main', __name__)

@bp.route("/")
def home():
    return render_template("index.html")

@bp.route("/manage_clups")
def manage_clups_page():
    return render_template("clups.html")

