import os
import random
import time
import logging
import threading
import traceback
from datetime import datetime
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from models import MongoDB
from utils import save_screenshot

# Initialize MongoDB
db = MongoDB()

# Initialize Flask app
app = Flask(__name__)

# Configure logging with more detailed output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",
    handlers=[
        logging.FileHandler("google_meet_automation.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class GoogleMeetAutomation:
    def __init__(self, headless=False):
        """
        Initialize Google Meet bot with headless option
        :param headless: If True, runs browser in headless mode
        """
        self.driver = None
        self.bot_id = None
        self.screenshot_folder = "./screenshots"
        self.captions_file = "./captions.txt"
        self.setup_browser(headless)

    def setup_browser(self, headless=False):
        """
        Setup Chrome WebDriver for Google Meet automation
        :param headless: If True, runs browser in headless mode
        """
        try:
            options = Options()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            if headless:
                options.add_argument("--headless")

            self.driver = webdriver.Chrome(options=options)
            logger.info("Browser initialized successfully.")
        except Exception as e:
            logger.error(f"Browser initialization failed: {e}")
            raise

    def join_meeting(self, meet_link, meeting_duration=30):
        """
        Automate joining a Google Meet meeting
        :param meet_link: URL of the Google Meet
        :param meeting_duration: Duration to stay in the meeting (minutes)
        :return: Status of the meeting join
        """
        try:
            self.bot_id = random.randint(1000, 9999)  # Generate a unique bot ID
            db.save_bot_status(self.bot_id, "running", meet_link)

            # Navigate to the Google Meet link
            self.driver.get(meet_link)
            time.sleep(3)

            # Take screenshot after loading the page
            self.take_screenshot("initial_page", meet_link)

            # Handle modal pop-ups in a separate thread
            modal_thread = threading.Thread(target=self.continuous_modal_handler)
            modal_thread.daemon = True
            modal_thread.start()

            # Wait for page to load and perform actions like entering a name
            time.sleep(3)
            self.enter_name()

            # Try to click the "Join Now" button
            if not self.click_join_button():
                raise Exception("Failed to click 'Join Now' button")

            # Mute audio and video before joining
            self.toggle_audio_video()
            time.sleep(3)

            # Enable captions after joining
            self.enable_captions()

            # Take a screenshot after joining the meeting
            self.take_screenshot("meeting_joined", meet_link)

            # Start capturing captions in a separate thread
            captions_thread = threading.Thread(target=self.capture_captions)
            captions_thread.daemon = True
            captions_thread.start()

            # Stay in the meeting for the specified duration
            time.sleep(meeting_duration * 60)

            # Stop the bot and update status in the database
            db.update_bot_status(self.bot_id, "stopped")
            return {"status": "success", "message": "Meeting joined successfully"}

        except Exception as e:
            logger.error(f"Meeting join failed: {e}")
            db.update_bot_status(self.bot_id, "failed")
            return {"status": "error", "message": str(e)}

    def continuous_modal_handler(self):
        """
        Continuously close modals and pop-ups that appear during the meeting
        """
        modal_selectors = [
            'button[jsname="m9ZlFb"]',  # Close Icon
            'button[jsname="S5tZuc"]',  # Close Icon
            'button[jsname="EszDEe"]',  # Got it
            'button[data-mdc-dialog-action="cancel"]',  # Dismiss modal
            'button[jsname="V67aGc"]',  # Continue without signing in
        ]

        while True:
            try:
                for selector in modal_selectors:
                    try:
                        modal = WebDriverWait(self.driver, 2).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        modal.click()
                        logger.info(f"Closed modal: {selector}")
                        time.sleep(0.5)
                    except (TimeoutException, NoSuchElementException):
                        continue
            except Exception as e:
                logger.error(f"Error in modal handler: {e}")
            time.sleep(1)

    def enter_name(self):
        """
        Enter a name for the guest in the input field
        """
        try:
            name_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'input[jsname="YPqjbf"]')
                )
            )
            self.driver.execute_script(
                "arguments[0].value = 'Automated Bot';", name_input
            )
            self.driver.execute_script(
                """
                var input = arguments[0];
                var event = new Event('input', { bubbles: true });
                input.dispatchEvent(event);
                """,
                name_input,
            )
        except Exception as e:
            logger.warning(f"Could not enter guest name: {e}")

    def click_join_button(self):
        """
        Try to click the "Join Now" button using multiple strategies
        """
        join_selectors = [
            'button[jsname="Qx7uuf"]',  # Primary selector
            'div[jsname="GGAcbc"]',  # Alternative selector
            ".UywwFc-LgbsSe",  # Class-based selector
        ]

        try:
            for selector in join_selectors:
                try:
                    join_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    self.driver.execute_script("arguments[0].click();", join_button)
                    time.sleep(2)  # Wait for the meeting to load
                    return True
                except Exception as e:
                    logger.warning(f"Join attempt with {selector} failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to click the 'Join Now' button: {e}")
            return False

    def take_screenshot(self, step_name, meet_link):
        """
        Capture and save a screenshot with a descriptive name
        """
        try:
            if not os.path.exists(self.screenshot_folder):
                os.makedirs(self.screenshot_folder)

            meet_id = meet_link.split("/")[-1]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.screenshot_folder}/{meet_id}_{step_name}_{timestamp}.png"
            self.driver.save_screenshot(filename)

            screenshot_data = save_screenshot(filename, self.bot_id)
            db.save_screenshot(self.bot_id, screenshot_data)
            logger.info(f"Screenshot saved: {filename}")
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")

    def toggle_audio_video(self):
        """
        Mute microphone and turn off camera
        """
        try:
            mic_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'div[jscontroller="t2mBxb"]')
                )
            )
            mic_button.click()

            cam_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'div[jscontroller="bwqwSd"]')
                )
            )
            cam_button.click()

            logger.info("Microphone and camera turned off")
        except Exception as e:
            logger.warning(f"Failed to toggle audio/video: {e}")

    def enable_captions(self):
        """
        Enable captions during the meeting
        """
        try:
            captions_button = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[jsname="r8qRAd"]'))
            )
            captions_button.click()
            logger.info("Captions enabled.")
        except Exception as e:
            logger.error(f"Failed to enable captions: {e}")

    def capture_captions(self):
        """
        Capture captions from the Google Meet in real-time and save them to MongoDB
        """
        try:
            while True:
                captions = self.driver.find_elements(
                    By.CSS_SELECTOR, 'div[jsname="YSxPC"] div[jsname="tgaKEf"] span'
                )
                if captions:
                    for caption in captions:
                        transcription = caption.text.strip()
                        if transcription:
                            db.save_transcription(self.bot_id, transcription)
                time.sleep(1)
        except Exception as e:
            logger.error(f"Error capturing captions: {e}")


# Flask Routes


@app.route("/join-meet", methods=["POST"])
def join_meet():
    """API to start a bot and join a Google Meet"""
    data = request.json
    meet_link = data.get("meet_link")
    duration = data.get("meeting_duration", 30)

    if not meet_link:
        return jsonify({"status": "error", "message": "meet_link is required"}), 400

    bot = GoogleMeetAutomation()
    result = bot.join_meeting(meet_link, duration)
    return jsonify(result)


@app.route("/active-bots", methods=["GET"])
def active_bots():
    """API to list active bots"""
    active_bots = db.get_active_bots()
    return jsonify({"active_bots": active_bots})


@app.route("/stop-bot", methods=["POST"])
def stop_bot():
    """API to stop a bot"""
    data = request.json
    bot_id = data.get("bot_id")

    if not bot_id:
        return jsonify({"status": "error", "message": "bot_id is required"}), 400

    db.update_bot_status(bot_id, "stopped")
    return jsonify({"status": "success", "message": "Bot stopped successfully"})
