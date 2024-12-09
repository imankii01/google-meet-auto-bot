import os
from datetime import datetime
from PIL import Image
import base64
import io

# Save screenshot as an image file
def save_screenshot(screenshot_data, bot_id):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'./screenshots/{bot_id}_{timestamp}.png'

    img_data = base64.b64decode(screenshot_data)
    with open(filename, 'wb') as f:
        f.write(img_data)

    return filename
