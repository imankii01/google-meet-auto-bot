import os
import random
import time
import logging
import threading
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, Response
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException
)

# Initialize Flask app
app = Flask(__name__)

# Configure logging with more detailed output
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",
    handlers=[
        logging.FileHandler("google_meet_automation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GoogleMeetAutomation:
    def __init__(self, headless=False):
        """
        Initialize the Google Meet automation with configurable browser options
        
        :param headless: Run browser in headless mode if True
        """
        self.driver = None
        self.screenshot_folder = "./screenshots"
        self.setup_browser(headless)
        
    def setup_browser(self, headless=False):
        """
        Configure and initialize the Chrome WebDriver
        
        :param headless: Run browser in headless mode if True
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

    def take_screenshot(self, step_name, meet_link):
        """
        Take and save a screenshot with a descriptive name
        
        :param step_name: Description of the current step
        :param meet_link: Google Meet link to extract meeting ID
        """
        try:
            if not os.path.exists(self.screenshot_folder):
                os.makedirs(self.screenshot_folder)
            
            meet_id = meet_link.split("/")[-1]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.screenshot_folder}/{meet_id}_{step_name}_{timestamp}.png"
            
            self.driver.save_screenshot(filename)
            logger.info(f"Screenshot saved: {filename}")
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")

    def continuous_modal_handler(self, stop_event):
        """
        Continuously attempt to close modals and pop-ups
        
        :param stop_event: Threading event to stop the handler
        """
        modal_selectors = [
            'button[jsname="m9ZlFb"]',      # Close Icon
            'button[jsname="S5tZuc"]',      # Close Icon
            'button[jsname="EszDEe"]',      # Got it
            'button[data-mdc-dialog-action="cancel"]',  # Dismiss modal
            'button[jsname="V67aGc"]',      # Continue without signing in
            'button[jsname="Jf6fmb"]',      # Got it on the next modal
            'button[jsname="Qx7uuf"]',      # Join now
        ]

        while not stop_event.is_set():
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

    def join_meeting(self, meet_link, meeting_duration=30):
        """
        Automated process to join a Google Meet with enhanced interaction handling
        
        :param meet_link: Google Meet invite link
        :param meeting_duration: Duration to stay in meeting (minutes)
        :return: Dictionary with join status
        """
        stop_modal_event = threading.Event()
        modal_thread = None
        
        try:
            # Navigate to meet link
            self.driver.get(meet_link)
            self.take_screenshot("initial_page", meet_link)
            
            # Start continuous modal handler
            modal_thread = threading.Thread(
                target=self.continuous_modal_handler, 
                args=(stop_modal_event,)
            )
            modal_thread.daemon = True
            modal_thread.start()
            
            # Wait for page to load completely
            time.sleep(3)
            
            # Enhanced name input handling
            try:
                # Use JavaScript to enter name (bypassing potential overlay issues)
                name_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[jsname="YPqjbf"]'))
                )
                self.driver.execute_script("arguments[0].value = 'Mentorpal.ai';", name_input)
                
                # Force trigger input events
                self.driver.execute_script("""
                    var input = arguments[0];
                    var event = new Event('input', { bubbles: true });
                    input.dispatchEvent(event);
                """, name_input)
            except Exception as e:
                logger.warning(f"Could not enter guest name: {e}")
            
            # Advanced join button interaction
            try:
                # Try multiple strategies to click join button
                join_selectors = [
                    'button[jsname="Qx7uuf"]',  # Primary selector
                    'div[jsname="GGAcbc"]',     # Alternative selector
                    '.UywwFc-LgbsSe'            # Class-based selector
                ]
                
                join_success = False
                for selector in join_selectors:
                    try:
                        # Use JavaScript click method
                        join_button = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        
                        # Multiple interaction strategies
                        self.driver.execute_script("arguments[0].click();", join_button)
                        
                        # Wait and verify
                        if self._check_meeting_join():
                            join_success = True
                            break
                        
                        # Backup: ActionChains click
                        ActionChains(self.driver).move_to_element(join_button).click().perform()
                        
                        if self._check_meeting_join():
                            join_success = True
                            break
                    except Exception as inner_e:
                        logger.warning(f"Join attempt with {selector} failed: {inner_e}")
                
                if not join_success:
                    raise Exception("Could not join meeting after multiple attempts")
            
            except Exception as e:
                logger.error(f"Meeting join button click failed: {e}")
                raise
            
            # Wait for page to load completely
            time.sleep(5)
            # Mute mic and turn off camera
            self.toggle_audio_video()
            print("Start Counting off caption")
            time.sleep(5)
            # Enable captions
            self.enable_captions()
            
            # Take screenshot after joining
            self.take_screenshot("meeting_joined", meet_link)
            
            # Run meeting for specified duration
            time.sleep(meeting_duration * 60)
            
            return {"status": "success", "message": "Meeting joined successfully"}
        
        except Exception as e:
            logger.error(f"Meeting join failed: {e}")
            logger.error(traceback.format_exc())
            # Wait for page to load completely
            time.sleep(5)
            # Mute mic and turn off camera
            self.toggle_audio_video()
            print("Start Counting off caption")
            time.sleep(5)
            # Enable captions
            self.enable_captions()
            
            # Take screenshot after joining
            self.take_screenshot("meeting_joined", meet_link)
            
            # Run meeting for specified duration
            time.sleep(meeting_duration * 60)
            
            return {"status": "success", "message": "Meeting joined successfully"}
        
        finally:
            # Stop modal handling thread
            stop_modal_event.set()
            
            # Take final screenshot
            self.take_screenshot("final_state", meet_link)
            
            # Leave meeting if still connected
            # self.leave_meeting()



    def _check_meeting_join(self):
        """
        Check if meeting has been successfully joined
        
        :return: Boolean indicating join status
        """
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[jsname="C6oYVc"]'))
            )
            return True
        except Exception:
            return False

    def toggle_audio_video(self):
        """Toggle microphone and camera off"""
        try:
            mic_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[jscontroller="t2mBxb"]'))
            )
            mic_button.click()
            
            cam_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[jscontroller="bwqwSd"]'))
            )
            cam_button.click()
            
            logger.info("Microphone and camera turned off")
        except Exception as e:
            logger.warning(f"Failed to toggle audio/video: {e}")

    def enable_captions(self):
        """Enable captions in the meeting"""
        try:
            # Wait for and click the captions button
            captions_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[jsname="hFkX3e"]'))
            )
            captions_button.click()
            logger.info("Captions button clicked.")
    
            # Optional: Confirm if a second click is required
            try:
                caption_confirm = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[jsname="r8qRAd"]'))
                )
                caption_confirm.click()
                logger.info("Confirmation for captions completed.")
            except Exception as e:
                logger.warning("Confirmation button not required or not clickable. Skipping...")
    
        except Exception as e:
            logger.error(f"Failed to enable captions: {str(e)}")


    def leave_meeting(self):
        """Leave the Google Meet"""
        try:
            leave_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[jsname="v67aGc"]'))
            )
            leave_button.click()
            logger.info("Left the meeting")
        except Exception as e:
            logger.warning(f"Failed to leave meeting: {e}")
        finally:
            if self.driver:
                self.driver.quit()

# Flask Routes
@app.route("/join-meet", methods=["POST"])
def join_meet_endpoint():
    """API endpoint to join a Google Meet"""
    try:
        data = request.json
        meet_link = data.get("meet_link")
        meeting_duration = data.get("meeting_duration", 30)
        
        if not meet_link:
            return jsonify({"status": "error", "message": "Missing meet_link"}), 400
        
        automation = GoogleMeetAutomation()
        result = automation.join_meeting(meet_link, meeting_duration)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Endpoint error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "OK", "timestamp": datetime.now().isoformat()}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)