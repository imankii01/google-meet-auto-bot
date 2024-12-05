from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os


def lambda_handler(event, context):
    # Extract the 'meet_link' from the request
    try:
        body = json.loads(event.get("body", "{}"))
        meet_link = body.get("meet_link")
        if not meet_link:
            raise ValueError("Missing 'meet_link' in request body")
    except Exception as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"status": "error", "message": str(e)}),
        }

    # Run the bot
    bot = JoinGoogleMeetAsGuest()
    try:
        result = bot.join_meet(meet_link)
    except Exception as e:
        result = {"status": "error", "message": str(e)}
    finally:
        bot.close()

    # Return the result
    return {"statusCode": 200, "body": json.dumps(result)}


class JoinGoogleMeetAsGuest:
    def __init__(self):
        # Set up ChromeDriver with AWS Lambda's headless Chromium
        chrome_options = Options()
        chrome_options.binary_location = "/opt/chromium/chrome"
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--single-process")
        chrome_options.add_argument("--disable-gpu")
        self.driver = webdriver.Chrome("/opt/chromedriver", options=chrome_options)

    def join_meet(self, meet_link):
        try:
            self.driver.get(meet_link)
            time.sleep(2)

            # Handle 'Join as Guest'
            try:
                self.driver.find_element(
                    By.CSS_SELECTOR, 'button[jsname="Qx7uuf"]'
                ).click()
                print("Joined as guest")
            except:
                print("Failed to click 'Join as Guest'")

            self.handle_modals()
            time.sleep(2)
            self.turn_off_mic_cam()
            time.sleep(5)

            return {
                "status": "success",
                "message": "Successfully joined the Google Meet",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def handle_modals(self):
        try:
            self.driver.find_element(
                By.CSS_SELECTOR,
                'button[data-mdc-dialog-action="cancel"] span.mUIrbf-vQzf8d',
            ).click()
            print("Closed 'Continue without microphone and camera' modal")
        except:
            pass
        try:
            continue_button = self.driver.find_element(
                By.CSS_SELECTOR, 'button[jsname="V67aGc"]'
            )
            continue_button.click()
            print("Clicked 'Continue without signing in'.")
        except:
            print("No 'Continue without signing in' modal.")
        try:
            name_field = self.driver.find_element(
                By.CSS_SELECTOR, 'input[jsname="YPqjbf"]'
            )
            name_field.send_keys("Guest Name")
            print("Entered name.")
        except:
            print("No 'Enter your name' field.")
        try:
            join_button = self.driver.find_element(
                By.CSS_SELECTOR, 'button[jsname="Qx7uuf"]'
            )
            join_button.click()
            print("Clicked 'Join now'.")
        except:
            print("Failed to click 'Join now'.")

    def turn_off_mic_cam(self):
        try:
            mic_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        'div[jscontroller="t2mBxb"][data-anchor-id="hw0c9"]',
                    )
                )
            )
            mic_button.click()
            print("Muted mic")
        except Exception as e:
            print(f"Error while muting mic: {e}")
        try:
            cam_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        'div[jscontroller="bwqwSd"][data-anchor-id="psRWwc"]',
                    )
                )
            )
            cam_button.click()
            print("Muted camera")
        except Exception as e:
            print(f"Error while muting camera: {e}")

    def close(self):
        self.driver.quit()
