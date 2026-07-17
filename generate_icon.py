import sys
import os

APP_DIR = r"C:\Users\LeviZ\protocol-7"
sys.path.append(APP_DIR)

from tray import create_image
img = create_image()
img.save(os.path.join(APP_DIR, "app.ico"), format="ICO", sizes=[(64, 64)])
