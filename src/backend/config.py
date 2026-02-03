import json
import os
from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "audio_device": None,
    "groq_api_key": "",
    "openrouter_api_key": "",
    "resume_path": "",
    "job_description": ""
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
