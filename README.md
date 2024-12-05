

# Google Meet Auto Bot

Google Meet Auto Bot is a Python-based automation tool built using Selenium and Flask. It simplifies joining Google Meet sessions as a guest user by automating the entire process, including handling pop-ups, entering a guest name, and disabling the microphone and camera. The project also provides an API endpoint for easy integration into other systems.

---

## Features
- **Automatic Joining**: Joins Google Meet sessions as a guest without manual intervention.
- **Mic and Camera Control**: Automatically turns off the microphone and camera before joining the meeting.
- **Pop-Up Handling**: Manages modals like "Join as Guest" and "Continue without signing in."
- **Debugging**: Captures screenshots during various steps for debugging.
- **Flask API**: Provides an API endpoint to trigger the bot programmatically.

---

## Requirements

### Software Prerequisites
- **Google Chrome**: Latest version of Google Chrome.
- **ChromeDriver**: ChromeDriver matching your Chrome version.
  - Download from [here](https://chromedriver.chromium.org/downloads).

### Python Dependencies
Install dependencies using the provided `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/imankii01/google-meet-auto-bot.git
   cd google-meet-auto-bot
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up ChromeDriver**:
   - Ensure `chromedriver` is in your system's PATH or update the script with the correct path.

---

## Usage

### 1. Running the Bot Script
To join a Google Meet session:
1. Update the Google Meet link in the script or pass it as an argument to the `join_meet` function.
2. Run the script:
   ```bash
   python bot.py
   ```

### 2. Using the Flask API
Start the Flask API server:
```bash
python app.py
```

Make a POST request to the API to initiate the bot:
```bash
curl -X POST http://127.0.0.1:5000/api/join-meet \
-H "Content-Type: application/json" \
-d '{"meet_link": "https://meet.google.com/example-link"}'
```

---

## Project Structure

```plaintext
google-meet-auto-bot/
│
├── bot.py               # Selenium-based bot script
├── app.py               # Flask API to control the bot
├── requirements.txt     # List of dependencies
└── README.md            # Documentation
```

---

## Configuration

### Logging
The project uses the `logging` module to provide detailed logs of the bot's actions. Logs are displayed in the console and can be configured to write to a file.

### Debugging
Screenshots are captured at various stages of execution and saved in the working directory. This helps in identifying issues during automation.

---

## Troubleshooting

### Common Issues
1. **Bot detected as automation**:
   - Ensure the `--disable-blink-features=AutomationControlled` Chrome option is included in the script.
2. **Element not found**:
   - Google Meet's UI may have changed. Update the selectors in the script accordingly.
3. **ChromeDriver mismatch**:
   - Ensure the ChromeDriver version matches your installed Chrome browser.

### Updating ChromeDriver
Download the appropriate version from [here](https://chromedriver.chromium.org/downloads) and replace the existing `chromedriver` binary.

---

## Contributing
Contributions are welcome! If you find a bug or have a feature request:
1. Fork the repository.
2. Create a new branch for your changes.
3. Submit a pull request with a detailed explanation.

---

## License
This project is licensed under the [MIT License](LICENSE). Feel free to use and modify the code.

---

## Author
Developed by [imankii01](https://github.com/imankii01).

For questions or feedback, feel free to raise an issue in the repository.

---
