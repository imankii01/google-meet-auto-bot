from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import os
from datetime import datetime


app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JoinGoogleMeetAsGuest:
    def __init__(self):
        logger.info("Initializing headless browser...")
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        # options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        # options.add_argument("--remote-debugging-port=9222")  # For debugging
        # options.add_argument(
        #     "--use-fake-ui-for-media-stream"
        # )  # Bypass mic/camera permission
        # options.add_argument("--disable-blink-features=AutomationControlled")

        # Set user-agent to mimic a real browser
        # options.add_argument(
        #     "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        # )

        try:
            self.driver = webdriver.Chrome(options=options)
            logger.info("Browser initialized successfully.")
        except Exception as e:
            logger.error("Failed to initialize browser: %s", e)
            raise

    def debug_screenshot(self, step_name):
        """Capture a screenshot for debugging."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"./screenshots/{step_name}_{timestamp}.png"
        os.makedirs("./screenshots", exist_ok=True)
        self.driver.save_screenshot(screenshot_path)
        logger.info(f"Screenshot saved: {screenshot_path}")

    def join_meet(self, meet_link):
        try:
            logger.info(f"Navigating to Google Meet link: {meet_link}")
            self.driver.get(meet_link)
            time.sleep(2)
            self.debug_screenshot("page_loaded")

            # Handle "Join as Guest" button
            self.click_button('button[jsname="Qx7uuf"]', "Join as Guest")
            self.debug_screenshot("join_as_guest_clicked")

            self.handle_modals()
            self.turn_off_mic_cam()

            # Confirm join status
            if self.check_join_status():
                logger.info("Successfully joined the Google Meet.")
                return {
                    "status": "success",
                    "message": "Successfully joined the Google Meet",
                }
            else:
                logger.error("Failed to confirm meeting join status.")
                return {
                    "status": "error",
                    "message": "Failed to join the meeting. Status not confirmed.",
                }

        except Exception as e:
            logger.error("An error occurred during the meeting join process: %s", e)
            return {"status": "error", "message": str(e)}
        finally:
            self.debug_screenshot("final_state")
            self.close()

    def click_button(self, selector, description):
        try:
            button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            button.click()
            logger.info(f"Clicked {description} button.")
        except Exception as e:
            logger.error(f"Failed to click {description} button: %s", e)

    def handle_modals(self):
        logger.info("Handling modals...")
        self.click_button(
            'button[data-mdc-dialog-action="cancel"] span.mUIrbf-vQzf8d',
            "Dismiss modal",
        )
        self.click_button('button[jsname="V67aGc"]', "Continue without signing in")
        self.enter_guest_name()
        self.click_button('button[jsname="Qx7uuf"]', "Join now")

    def enter_guest_name(self):
        try:
            name_field = self.driver.find_element(
                By.CSS_SELECTOR, 'input[jsname="YPqjbf"]'
            )
            name_field.send_keys("Guest Name")
            logger.info("Entered guest name.")
        except Exception as e:
            logger.error("Failed to find or fill guest name field: %s", e)

    def turn_off_mic_cam(self):
        logger.info("Turning off microphone and camera...")
        try:
            mic_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'div[jscontroller="t2mBxb"]')
                )
            )
            mic_button.click()
            logger.info("Microphone muted.")
        except Exception as e:
            logger.error("Error while muting mic: %s", e)

        try:
            cam_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'div[jscontroller="bwqwSd"]')
                )
            )
            cam_button.click()
            logger.info("Camera turned off.")
        except Exception as e:
            logger.error("Error while turning off camera: %s", e)

    def check_join_status(self):
        logger.info("Verifying meeting join status...")
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div[jsname="C6oYVc"]')
                )  # Example: meeting participant list
            )
            logger.info("Join status confirmed.")
            return True
        except Exception as e:
            logger.error("Join status not confirmed: %s", e)
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
        return (
            jsonify(
                {"status": "error", "message": "Missing 'meet_link' in request body"}
            ),
            400,
        )

    bot = JoinGoogleMeetAsGuest()
    result = bot.join_meet(meet_link)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True),