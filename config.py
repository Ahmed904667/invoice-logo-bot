import os
from pathlib import Path
from dotenv import load_dotenv

import sys

# Base directory: handles normal python script execution and PyInstaller .exe bundle
if getattr(sys, "frozen", False):
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    EXE_DIR = Path(sys.executable).parent
    # Prioritize external invoiceBg next to the .exe, otherwise use bundled template
    BASE_DIR = EXE_DIR if any((EXE_DIR / f"invoiceBg{ext}").exists() for ext in [".jpeg", ".jpg", ".pdf", ".png"]) else BUNDLE_DIR
else:
    BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# Default Background File Path (can be PDF, JPEG, PNG, etc.)
DEFAULT_BG_NAME = os.getenv("DEFAULT_BG_NAME", "invoiceBg.jpeg")
BACKGROUND_IMAGE_PATH = BASE_DIR / DEFAULT_BG_NAME


def get_background_path() -> Path:
    """Returns the currently active background path, searching fallback extensions if needed."""
    global BACKGROUND_IMAGE_PATH
    if BACKGROUND_IMAGE_PATH.exists():
        return BACKGROUND_IMAGE_PATH
    # Look for common background filenames
    for ext in [".pdf", ".jpeg", ".jpg", ".png", ".webp"]:
        candidate = BASE_DIR / f"invoiceBg{ext}"
        if candidate.exists():
            BACKGROUND_IMAGE_PATH = candidate
            return candidate
    return BACKGROUND_IMAGE_PATH


def set_background_path(new_path: Path):
    """Update active background path in memory."""
    global BACKGROUND_IMAGE_PATH
    BACKGROUND_IMAGE_PATH = Path(new_path)

# Temporary / Output directory for processed files
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# Allowed User IDs (comma-separated integers in .env, e.g. "12345678,87654321")
# If empty, the bot is open to all users.
_allowed_users_raw = os.getenv("ALLOWED_USER_IDS", "").strip()
if _allowed_users_raw:
    ALLOWED_USER_IDS = {
        int(uid.strip())
        for uid in _allowed_users_raw.split(",")
        if uid.strip().isdigit()
    }
else:
    ALLOWED_USER_IDS = set()

# Admin User IDs (can change background with /setbg)
_admin_users_raw = os.getenv("ADMIN_USER_IDS", "").strip()
if _admin_users_raw:
    ADMIN_USER_IDS = {
        int(uid.strip())
        for uid in _admin_users_raw.split(",")
        if uid.strip().isdigit()
    }
else:
    ADMIN_USER_IDS = ALLOWED_USER_IDS.copy()

# Max file size accepted by the bot in Megabytes (default 20MB, Telegram bot limit)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))


def is_user_allowed(user_id: int) -> bool:
    """Check if a given Telegram user ID is authorized to use the bot."""
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS


def is_user_admin(user_id: int) -> bool:
    """Check if a given Telegram user ID has admin privileges."""
    if not ADMIN_USER_IDS:
        return True
    return user_id in ADMIN_USER_IDS
