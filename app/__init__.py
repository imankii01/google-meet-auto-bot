from flask import Flask

def create_app():
    """
    Create and configure the Flask application.
    """
    app = Flask(__name__)

    # Register blueprints
    from .routes import api

    app.register_blueprint(api)

    return app
