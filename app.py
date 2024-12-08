from app import create_app
from config.logging_config import configure_logging

if __name__ == "__main__":
    # Configure logging
    configure_logging()

    # Create Flask app instance
    app = create_app()

    # Run the Flask application
    app.run(host="0.0.0.0", port=5000, debug=True)
