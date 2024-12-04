from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

app = Flask(__name__)

class JoinGoogleMeetAsGuest:
    def __init__(self):
        opt = Options()
        opt.add_argument('--disable-blink-features=AutomationControlled')
        opt.add_argument('--start-maximized')
        # You can add more options like running in headless mode if needed:
        # opt.add_argument('--headless')
        self.driver = webdriver.Chrome(options=opt)

    def join_meet(self, meet_link):
        try:
            self.driver.get(meet_link)
            time.sleep(2)
            
            # Handle 'Join as Guest'
            try:
                self.driver.find_element(By.CSS_SELECTOR, 'button[jsname="Qx7uuf"]').click()
                print("Joined as guest")
            except:
                print("Failed to click 'Join as Guest'")

            self.handle_modals()

            # Wait for elements to appear before interacting with them
            time.sleep(2)
            self.turn_off_mic_cam()

            # Wait for the meeting to load
            time.sleep(5)
            return {"status": "success", "message": "Successfully joined the Google Meet"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def handle_modals(self):
        try:
            self.driver.find_element(By.CSS_SELECTOR, 'button[data-mdc-dialog-action="cancel"] span.mUIrbf-vQzf8d').click()
            print("Closed 'Continue without microphone and camera' modal")
        except:
            pass

        try:
            continue_without_sign_in_button = self.driver.find_element(By.CSS_SELECTOR, 'button[jsname="V67aGc"]')
            continue_without_sign_in_button.click()
            print("Clicked 'Continue without signing in'.")
        except:
            print("No 'Continue without signing in' modal.")

        try:
            sign_in_modal_button = self.driver.find_element(By.CSS_SELECTOR, 'button[jsname="LgbsSe"]')
            sign_in_modal_button.click()
            print("Clicked Google sign-in modal (skipped).")
        except:
            print("No Google sign-in modal.")

        try:
            allow_mic_button = self.driver.find_element(By.CSS_SELECTOR, 'div[jsname="D2uE7c"]')
            allow_mic_button.click()
            print("Microphone permission granted.")
        except:
            print("No microphone permission popup or already handled.")

        try:
            allow_cam_button = self.driver.find_element(By.CSS_SELECTOR, 'div[jsname="zYDCMe"]')
            allow_cam_button.click()
            print("Camera permission granted.")
        except:
            print("No camera permission popup or already handled.")

        try:
            name_field = self.driver.find_element(By.CSS_SELECTOR, 'input[jsname="YPqjbf"]')
            name_field.send_keys("Guest Name")
            print("Entered name.")
        except:
            print("No 'Enter your name' field or already handled.")

        try:
            join_button = self.driver.find_element(By.CSS_SELECTOR, 'button[jsname="Qx7uuf"]')
            join_button.click()
            print("Clicked 'Join now'.")
        except:
            print("Failed to click 'Join now'.")

    def turn_off_mic_cam(self):
        try:
            mic_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[jscontroller="t2mBxb"][data-anchor-id="hw0c9"]'))
            )
            mic_button.click()
            print("Muted mic")
        except Exception as e:
            print(f"Error while muting mic: {e}")

        try:
            cam_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[jscontroller="bwqwSd"][data-anchor-id="psRWwc"]'))
            )
            cam_button.click()
            print("Muted camera")
        except Exception as e:
            print(f"Error while muting camera: {e}")

    def close(self):
        self.driver.quit()

# Flask API Route
@app.route('/join-meet', methods=['POST'])
def join_meet():
    data = request.json
    meet_link = data.get('meet_link')

    if not meet_link:
        return jsonify({"status": "error", "message": "Missing 'meet_link' in request body"}), 400

    bot = JoinGoogleMeetAsGuest()
    result = bot.join_meet(meet_link)
    bot.close()

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
