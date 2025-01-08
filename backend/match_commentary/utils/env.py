import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_FOOTBALL_BASE_URL = os.getenv("API_FOOTBALL_BASE_URL")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")