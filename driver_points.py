import json
import logging
import os
import time
from pathlib import Path

import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("driver_standings_fetch.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.jolpi.ca/ergast/f1"
RATE_LIMIT_BURST = 2  # requests per second
RATE_LIMIT_SUSTAINED = 500  # requests per hour
REQUEST_DELAY = 1 / RATE_LIMIT_BURST  # seconds between requests


def create_folder_if_not_exists(folder_path):
    """Create folder if it doesn't exist"""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        logger.info(f"Created folder: {folder_path}")


def get_race_folder_name(race):
    """Convert race name to folder name format"""
    return race["raceName"].lower().replace(" ", "-")


def fetch_with_rate_limit(url):
    """Fetch data with rate limiting"""
    logger.info(f"Fetching: {url}")
    time.sleep(REQUEST_DELAY)  # Respect rate limit
    response = requests.get(url)

    if response.status_code == 429:
        logger.warning("Rate limit exceeded. Waiting 30 seconds before retrying...")
        time.sleep(30)
        return fetch_with_rate_limit(url)

    if response.status_code != 200:
        logger.error(f"Error fetching {url}: {response.status_code} - {response.text}")
        return None

    return response.json()


def fetch_driver_standings(season, round_num):
    """Fetch driver standings for a specific round in a season"""
    url = f"{BASE_URL}/{season}/{round_num}/driverstandings/"
    return fetch_with_rate_limit(url)


def process_round(season, round_num):
    """Process a specific round in a season"""
    logger.info(f"Processing season: {season}, round: {round_num}")

    # Create season folder
    season_folder = Path(f"{season}")
    create_folder_if_not_exists(season_folder)

    # Fetch events data for the season
    events_file = season_folder / "events.json"
    if not events_file.exists():
        logger.warning(f"Events file not found for season {season}. Skipping.")
        return

    with open(events_file, "r") as f:
        events_data = json.load(f)

    races = events_data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    if not races:
        logger.warning(f"No races found for season {season}. Skipping.")
        return

    # Find the specific race for the round
    race = None
    for r in races:
        if r.get("round") == str(round_num):
            race = r
            break

    if not race:
        logger.warning(f"Round {round_num} not found for season {season}. Skipping.")
        return

    race_folder_name = get_race_folder_name(race)
    race_folder = season_folder / race_folder_name
    create_folder_if_not_exists(race_folder)

    # Fetch round-level driver standings
    round_standings = fetch_driver_standings(season, round_num)
    if round_standings:
        with open(race_folder / "driverPoints.json", "w") as f:
            json.dump(round_standings, f, indent=2)
            logger.info(
                f"Saved round driver standings to {race_folder}/driverPoints.json"
            )


if __name__ == "__main__":
    logger.info("Starting driver standings fetch script for specific round")
    # process_round(2025, 13)
    # process_round(2025, 14)
    # process_round(2025, 15)
    # process_round(2025, 16)
    # process_round(2025, 17)
    # process_round(2025, 18)
    process_round(2025, 19)
    # process_round(2025, 20)
    # process_round(2025, 21)
    # process_round(2025, 22)
    # process_round(2025, 23)
    # process_round(2025, 24)



    logger.info("Completed driver standings fetch script")
