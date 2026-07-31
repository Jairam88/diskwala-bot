import os

API_ID_RAW = os.environ.get("30918158", "").strip()
API_HASH = os.environ.get("795178cb0ef1cc68690b1bbe82960214", "").strip()
BOT_TOKEN = os.environ.get("7999558903:AAFmnpddylgWzlofbslPYtviziARBYya-i0", "").strip()

try:
    API_ID = int(API_ID_RAW) if API_ID_RAW else 0
except ValueError:
    API_ID = 0
  
