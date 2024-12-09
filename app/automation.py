import os
import random
import time
import uuid
import logging
import threading
import traceback
from datetime import datetime
import pymongo
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
    def __init__(self, headless=False):
        """
        Initialize the Google Meet automation with configurable browser options

        :param headless: Run browser in headless mode if True
        """
        self.bot_id = str(uuid.uuid4())
        self.status = "initialized"
        self.driver = None
        self.mongo_client = pymongo.MongoClient("mongodb+srv://codewithankit047:nVhYb1cI7bl1VXdy@cluster0.fnsfc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
        self.db = self.mongo_client["google_meet_bot"]

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
            # Save to MongoDB
            with open(filename, "rb") as image_file:
                screenshot_data = {
                    "bot_id": self.bot_id,
                    "step_name": step_name,
                    "meet_link": meet_link,
                    "timestamp": datetime.now(),
                    "screenshot": image_file.read(),
                }
                self.db.screenshots.insert_one(screenshot_data)

            logger.info(f"Screenshot saved: {filename}")
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")

    def continuous_modal_handler(self, stop_event):
        """
        Continuously attempt to close modals and pop-ups

        :param stop_event: Threading event to stop the handler
        """
        modal_selectors = [
            'button[jsname="m9ZlFb"]',
            'button[jsname="S5tZuc"]',
            'button[jsname="EszDEe"]',
            'button[data-mdc-dialog-action="cancel"]',
            'button[jsname="V67aGc"]',
            'button[jsname="Jf6fmb"]',
            'button[jsname="Qx7uuf"]',
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
        self.status = "joining"
        stop_modal_event = threading.Event()
        modal_thread = None
        captions_thread = None
        stop_captions_event = threading.Event()
        try:
            self.driver.get(meet_link)
            self.take_screenshot("initial_page", meet_link)

            modal_thread = threading.Thread(
                target=self.continuous_modal_handler, args=(stop_modal_event,)
            )
            modal_thread.daemon = True
            modal_thread.start()

            time.sleep(3)

            try:
                name_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'input[jsname="YPqjbf"]')
                    )
                )
                self.driver.execute_script(
                    "arguments[0].value = 'Mentorpal.ai';", name_input
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

            try:
                join_selectors = [
                    'button[jsname="Qx7uuf"]',
                    'div[jsname="GGAcbc"]',
                    ".UywwFc-LgbsSe",
                ]

                join_success = False
                for selector in join_selectors:
                    try:
                        join_button = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        self.driver.execute_script("arguments[0].click();", join_button)
                        if self._check_meeting_join():
                            join_success = True
                            break
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

            time.sleep(5)
            print("Start Counting off caption")
            time.sleep(5)
            self.enable_captions()

            self.take_screenshot("meeting_joined", meet_link)
            captions_thread = threading.Thread(
                target=self.capture_captions, args=(stop_captions_event,meet_link)
            )
            captions_thread.start()
            time.sleep(meeting_duration * 60)

            return {"status": "success", "message": "Meeting joined successfully"}

        except Exception as e:
            logger.error(f"Meeting join failed: {e}")
            logger.error(traceback.format_exc())
            time.sleep(5)
            print("Start Counting off caption")
            time.sleep(5)
            self.enable_captions()

            self.take_screenshot("meeting_joined", meet_link)
            captions_thread = threading.Thread(
                target=self.capture_captions, args=(stop_captions_event,meet_link)
            )
            captions_thread.start()
            time.sleep(meeting_duration * 60)

            return {"status": "success", "message": "Meeting joined successfully"}

        finally:
            stop_modal_event.set()

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

    def capture_captions(self, stop_event,meet_link):
        """Capture captions in real-time and save to a file."""
        try:
            os.makedirs(os.path.dirname(self.captions_file), exist_ok=True)
            logger.info(f"Captions will be saved to: {self.captions_file}")

            with open(self.captions_file, "w") as f:
                logger.info("Started capturing captions.")
                while not stop_event.is_set():
                    try:
                        captions = self.driver.find_elements(
                            By.CSS_SELECTOR,
                            'div[jsname="YSxPC"] div[jsname="tgaKEf"] span',
                        )
                        if captions:
                            logger.debug(f"Captions found: {len(captions)}")
                            for caption in captions:
                                text = caption.text.strip()
                                if text:
                                    f.write(text + "\n")
                                    f.flush()
                                else:
                                    logger.warning("Empty caption found.")
                        else:
                            logger.warning("No captions found.")

                        caption_documents = [
                            {
                                "bot_id": self.bot_id,
                                "meet_link": meet_link,
                                "timestamp": datetime.now(),
                                "text": caption.text.strip(),
                            }
                            for caption in captions
                            if caption.text.strip()
                        ]

                        if caption_documents:
                            self.db.captions.insert_many(caption_documents)

                        time.sleep(1)
                    except Exception as e:
                        logger.warning(f"Error while capturing captions: {e}")
                        time.sleep(1)
        except Exception as e:
            logger.error(f"Error capturing captions: {e}")
