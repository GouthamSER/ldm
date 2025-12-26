import os

def get_env_variable(var_name, default_value=None):
    return os.environ.get(var_name, default_value)

# =================
# Telegram Credentials
# =================
API_ID = int(get_env_variable("API_ID", 1234567)) 
API_HASH = get_env_variable("API_HASH", "YOUR_API_HASH") 
BOT_TOKEN = get_env_variable("BOT_TOKEN", "YOUR_BOT_TOKEN") 
OWNER_ID = int(get_env_variable("OWNER_ID", 123456789))

# =================
# Aria2 RPC Configuration
# =================
ARIA2_HOST = get_env_variable("ARIA2_HOST", "127.0.0.1")
ARIA2_PORT = int(get_env_variable("ARIA2_PORT", 6801)) # DONT CHANGEEE !!!!
ARIA2_SECRET = get_env_variable("ARIA2_SECRET", "gjld")

# =================
# Bot Operational Settings
# =================
DOWNLOAD_DIR = get_env_variable("DOWNLOAD_DIR", "./downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
SESSION_NAME = get_env_variable("SESSION_NAME", "ariadwd")

# Web/Health Check Port (used in the provided bot.py and plugins.weblive)
HEALTH_PORT = int(get_env_variable("PORT", 8000))
