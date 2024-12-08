import logging
import os

def configure_logging():
    """
    Configure logging for the application with a dedicated 'logs' folder.
    """
    # Ensure the 'logs' folder exists
    log_folder = "logs"
    os.makedirs(log_folder, exist_ok=True)

    # Define the log file path
    log_file = os.path.join(log_folder, "google_meet_automation.log")

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )
    logging.info("Logging configured successfully. Logs will be stored in the 'logs' folder.")
