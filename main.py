import os
import random
import time
import logging
import threading
from datetime import datetime
from flask import Flask, request, jsonify,Response
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Health check route
@app.route("/health", methods=["GET"])
def health_check():
    """
    Check if the server is running.
    Responds with a simple HTML page indicating if the server is online.
    """
    try:
        # Here you can add additional health checks like database connectivity, etc.
        response = """
        <html>
        <head><title>Health Check</title></head>
        <body>
            <h1 style="color: green;">Server is UP</h1>
            <p>Status: OK</p>
            <p>Time: {}</p>
        </body>
        </html>
        """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return Response(response, status=200, content_type='text/html')
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        response = """
        <html>
        <head><title>Health Check</title></head>
        <body>
            <h1 style="color: red;">Server is DOWN</h1>
            <p>Status: ERROR</p>
            <p>Time: {}</p>
            <p>Error: {}</p>
        </body>
        </html>
        """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(e))
        
        return Response(response, status=500, content_type='text/html')

# Random delay function to mimic human behavior
def random_sleep(min_seconds=1, max_seconds=3):
    time.sleep(random.uniform(min_seconds, max_seconds))

# Class to automate the process of joining Google Meet as a guest
class JoinGoogleMeetAsGuest:
    def __init__(self):
        logger.info("Initializing headless browser...")

        options = Options()
        
        options.add_argument("--headless")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled") 
        options.add_experimental_option("excludeSwitches", ["enable-automation"])


        try:
            self.driver = webdriver.Chrome(options=options)
            logger.info("Browser initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    def debug_screenshot(self, step_name, meet_link):
        """Capture a screenshot for debugging with meet_link in filename."""
        meet_id = meet_link.split('/')[-1]  # Extract the meeting ID from the link
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Create a folder for the meeting if it doesn't exist
        folder_path = f"./screenshots/{meet_id}"
        os.makedirs(folder_path, exist_ok=True)
        screenshot_path = f"{folder_path}/{step_name}_{meet_id}_{timestamp}.png"
        self.driver.save_screenshot(screenshot_path)
        logger.info(f"Screenshot saved: {screenshot_path}")

    def capture_screenshots_periodically(self, meet_link):
        """Capture screenshots every 4 seconds with meeting ID and timestamp as filename."""
        meet_id = meet_link.split('/')[-1]  # Extract the meeting ID from the link
        folder_path = f"./screenshots/{meet_id}"
        os.makedirs(folder_path, exist_ok=True)  # Ensure the meeting folder exists
        
        while True:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"{folder_path}/{meet_id}_{timestamp}.png"
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")
            time.sleep(4)  # Wait for 4 seconds before taking the next screenshot

    def join_meet(self, meet_link):
        try:
            logger.info(f"Navigating to Google Meet link: {meet_link}")
            self.driver.get(meet_link)
            random_sleep(2, 5)  # Simulate realistic wait time
            self.debug_screenshot("page_loaded",meet_link)
            
            # Start capturing screenshots periodically
            screenshot_thread = threading.Thread(target=self.capture_screenshots_periodically, args=(meet_link,))
            screenshot_thread.daemon = True  # This will allow the thread to exit when the main program exits
            screenshot_thread.start()

            # Handle "Join as Guest" button
            self.click_button('button[jsname="Qx7uuf"]', "Join as Guest")
            self.debug_screenshot("join_as_guest_clicked",meet_link)

            self.handle_modals()
            self.turn_off_mic_cam()

            # Confirm join status
            if self.check_join_status():
                logger.info("Successfully joined the Google Meet.")
                return {"status": "success", "message": "Successfully joined the Google Meet"}
            else:
                logger.error("Failed to confirm meeting join status.")
                return {"status": "error", "message": "Failed to join the meeting. Status not confirmed."}

        except Exception as e:
            logger.error(f"An error occurred during the meeting join process: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            self.debug_screenshot("final_state",meet_link)
            self.close()

    def click_button(self, selector, description):
        try:
            button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            button.click()
            logger.info(f"Clicked {description} button.")
        except Exception as e:
            logger.error(f"Failed to click {description} button: {e}")

    def handle_modals(self):
        logger.info("Handling modals...")
        self.click_button('button[data-mdc-dialog-action="cancel"] span.mUIrbf-vQzf8d', "Dismiss modal")
        self.click_button('button[jsname="V67aGc"]', "Continue without signing in")
        self.enter_guest_name()
        self.click_button('button[jsname="Qx7uuf"]', "Join now")

    def enter_guest_name(self):
        try:
            name_field = self.driver.find_element(By.CSS_SELECTOR, 'input[jsname="YPqjbf"]')
            name_field.send_keys("Guest Name")
            logger.info("Entered guest name.")
        except Exception as e:
            logger.error(f"Failed to find or fill guest name field: {e}")

    def turn_off_mic_cam(self):
        logger.info("Turning off microphone and camera...")
        try:
            mic_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[jscontroller="t2mBxb"]'))
            )
            mic_button.click()
            logger.info("Microphone muted.")
        except Exception as e:
            logger.error(f"Error while muting mic: {e}")

        try:
            cam_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[jscontroller="bwqwSd"]'))
            )
            cam_button.click()
            logger.info("Camera turned off.")
        except Exception as e:
            logger.error(f"Error while turning off camera: {e}")

    def check_join_status(self):
        logger.info("Verifying meeting join status...")
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[jsname="C6oYVc"]'))
            )  # Example: meeting participant list
            logger.info("Join status confirmed.")
            return True
        except Exception as e:
            logger.error(f"Join status not confirmed: {e}")
            return False

    def close(self):
        self.driver.quit()
        logger.info("Browser closed.")

# Flask API Route
@app.route("/join-meet", methods=["POST"])
def join_meet():
    data = request.json
    meet_link = data.get("meet_link")

    if not meet_link:
        logger.error("Missing 'meet_link' in request body.")
        return jsonify({"status": "error", "message": "Missing 'meet_link' in request body"}), 400

    bot = JoinGoogleMeetAsGuest()
    result = bot.join_meet(meet_link)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
