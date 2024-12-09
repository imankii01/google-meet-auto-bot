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
    WebDriverException,
)

logger = logging.getLogger(__name__)


class GoogleMeetAutomation:
    def __init__(self, headless=True):
        """
        Initialize the Google Meet automation with configurable browser options

        :param headless: Run browser in headless mode if True
        """
        self.driver = None
        self.screenshot_folder = "./screenshots"
        self.captions_file = "./captions.txt"
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
            'button[jsname="m9ZlFb"]',  # Close Icon
            'button[jsname="S5tZuc"]',  # Close Icon
            'button[jsname="EszDEe"]',  # Got it
            'button[data-mdc-dialog-action="cancel"]',  # Dismiss modal
            'button[jsname="V67aGc"]',  # Continue without signing in
            'button[jsname="Jf6fmb"]',  # Got it on the next modal
            'button[jsname="Qx7uuf"]',  # Join now
            # 'button[jsname="r8qRAd"]',      # caption now
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
        captions_thread = None
        stop_captions_event = threading.Event()
        try:
            # Navigate to meet link
            self.driver.get(meet_link)
            self.take_screenshot("initial_page", meet_link)

            # Start continuous modal handler
            modal_thread = threading.Thread(
                target=self.continuous_modal_handler, args=(stop_modal_event,)
            )
            modal_thread.daemon = True
            modal_thread.start()

            # Wait for page to load completely
            time.sleep(3)

            # Enhanced name input handling
            try:
                # Use JavaScript to enter name (bypassing potential overlay issues)
                name_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'input[jsname="YPqjbf"]')
                    )
                )
                self.driver.execute_script(
                    "arguments[0].value = 'Mentorpal.ai';", name_input
                )

                # Force trigger input events
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

            # Advanced join button interaction
            try:
                # Try multiple strategies to click join button
                join_selectors = [
                    'button[jsname="Qx7uuf"]',  # Primary selector
                    'div[jsname="GGAcbc"]',  # Alternative selector
                    ".UywwFc-LgbsSe",  # Class-based selector
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
                        ActionChains(self.driver).move_to_element(
                            join_button
                        ).click().perform()

                        if self._check_meeting_join():
                            join_success = True
                            break
                    except Exception as inner_e:
                        logger.warning(
                            f"Join attempt with {selector} failed: {inner_e}"
                        )

                if not join_success:
                    raise Exception("Could not join meeting after multiple attempts")

            except Exception as e:
                logger.error(f"Meeting join button click failed: {e}")
                raise

            # Wait for page to load completely
            time.sleep(5)
            # Mute mic and turn off camera
            print("Start Counting off caption")
            time.sleep(5)
            # Enable captions
            self.enable_captions()

            # Take screenshot after joining
            self.take_screenshot("meeting_joined", meet_link)
            # Start capturing captions
            captions_thread = threading.Thread(
                target=self.capture_captions, args=(stop_captions_event,)
            )
            captions_thread.start()

            # Stay in meeting for the specified duration
            # Run meeting for specified duration
            time.sleep(meeting_duration * 60)

            return {"status": "success", "message": "Meeting joined successfully"}

        except Exception as e:
            logger.error(f"Meeting join failed: {e}")
            logger.error(traceback.format_exc())
            # Wait for page to load completely
            time.sleep(5)
            # Mute mic and turn off camera
            print("Start Counting off caption")
            time.sleep(5)
            # Enable captions
            self.enable_captions()

            # Take screenshot after joining
            self.take_screenshot("meeting_joined", meet_link)
            captions_thread = threading.Thread(
                target=self.capture_captions, args=(stop_captions_event,)
            )
            captions_thread.start()
            # Run meeting for specified duration
            time.sleep(meeting_duration * 60)

            return {"status": "success", "message": "Meeting joined successfully"}

        finally:
            # Stop modal handling thread
            stop_modal_event.set()

            # Take final screenshot
            self.take_screenshot("final_state", meet_link)
            stop_captions_event.set()
            if captions_thread:
                captions_thread.join()

    def _check_meeting_join(self):
        """
        Check if meeting has been successfully joined

        :return: Boolean indicating join status
        """
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div[jsname="C6oYVc"]')
                )
            )
            return True
        except Exception:
            return False

    def enable_captions(self):
        """Enable captions in the meeting"""
        try:
            captions_button = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[jsname="r8qRAd"]'))
            )
            captions_button.click()
            logger.info("Captions enabled.")
        except Exception as e:
            logger.error(f"Failed to enable captions: {e}")

    def capture_captions(self, stop_event):
        """Capture captions in real-time and save to a file."""
        try:
            os.makedirs(os.path.dirname(self.captions_file), exist_ok=True)
            logger.info(f"Captions will be saved to: {self.captions_file}")

            with open(self.captions_file, "w") as f:
                logger.info("Started capturing captions.")
                while not stop_event.is_set():
                    try:
                        # Use the updated CSS selector to capture captions
                        captions = self.driver.find_elements(
                            By.CSS_SELECTOR,
                            'div[jsname="YSxPC"] div[jsname="tgaKEf"] span',
                        )
                        if captions:
                            logger.debug(f"Captions found: {len(captions)}")
                            for caption in captions:
                                text = caption.text.strip()
                                if text:  # Only write non-empty text
                                    f.write(text + "\n")
                                    f.flush()
                                else:
                                    logger.warning("Empty caption found.")
                        else:
                            logger.warning("No captions found.")
                        time.sleep(1)  # Add delay to reduce the load on the browser
                    except Exception as e:
                        logger.warning(f"Error while capturing captions: {e}")
                        time.sleep(1)
        except Exception as e:
            logger.error(f"Error capturing captions: {e}")
