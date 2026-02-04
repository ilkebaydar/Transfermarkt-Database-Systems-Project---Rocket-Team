from flask import Flask
from dotenv import load_dotenv
import os
from .views import main
from .views import transfers
from .views import games
from .views import players
from .views import clubs

load_dotenv()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object('config.DevelopmentConfig')

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass


    app.register_blueprint(main.bp)
    app.register_blueprint(transfers.transfers_bp)
    app.register_blueprint(games.games_bp)    
    app.register_blueprint(players.players_bp)
    app.register_blueprint(clubs.clubs_bp)
    
    return app