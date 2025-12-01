import json
import logging
import os
import time
from pathlib import Path

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("constructor_standings_fetcher.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Base URL for the Ergast API
BASE_URL = "https://api.jolpi.ca/ergast/f1"

# Rate limiting parameters
BURST_LIMIT = 2  # requests per second
SUSTAINED_LIMIT = 500  # requests per hour
REQUEST_DELAY = 1 / BURST_LIMIT  # seconds between requests


class ConstructorStandingsFetcher:
    def __init__(self, base_dir="data"):
        self.base_dir = Path(base_dir)
        self.requests_this_hour = 0
        self.hour_start_time = time.time()

    def reset_hour_counter_if_needed(self):
        """Reset the hourly request counter if an hour has passed"""
        current_time = time.time()
        if current_time - self.hour_start_time > 3600:  # 3600 seconds = 1 hour
            self.requests_this_hour = 0
            self.hour_start_time = current_time
            logger.info("Hourly request counter reset")

    def check_rate_limits(self):
        """Check if we're within rate limits, wait if necessary"""
        self.reset_hour_counter_if_needed()

        # Check sustained (hourly) limit
        if self.requests_this_hour >= SUSTAINED_LIMIT:
            wait_time = 1800 - (time.time() - self.hour_start_time)
            if wait_time > 0:
                logger.warning(
                    f"Hourly rate limit reached. Waiting {wait_time:.2f} seconds"
                )
                time.sleep(wait_time)
                self.requests_this_hour = 0
                self.hour_start_time = time.time()

        # Always wait between requests to respect burst limit
        time.sleep(REQUEST_DELAY)

    def make_request(self, url):
        """Make a request to the API with rate limiting"""
        self.check_rate_limits()

        try:
            response = requests.get(url)
            self.requests_this_hour += 1

            if response.status_code == 429:
                logger.error(
                    "Rate limit exceeded despite precautions. Waiting 30 seconds."
                )
                time.sleep(30)
                return self.make_request(url)  # Retry after waiting

            if response.status_code != 200:
                logger.error(
                    f"Error fetching data: {response.status_code} - {response.text}"
                )
                return None

            return response.json()

        except Exception as e:
            logger.error(f"Exception during request: {str(e)}")
            return None

    def get_race_info(self, season, round_num):
        """Get race information for a specific season and round"""
        url = f"{BASE_URL}/{season}/{round_num}.json"
        data = self.make_request(url)

        if not data:
            return None

        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        if races:
            return races[0]
        return None

    def get_constructor_standings(self, season, round_num):
        """Get constructor standings for a specific season and round"""
        url = f"{BASE_URL}/{season}/{round_num}/constructorstandings.json"
        return self.make_request(url)

    def save_json(self, data, filepath):
        """Save JSON data to a file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved data to {filepath}")

    def fetch_standings_by_round(self, season, round_num):
        """Fetch constructor standings for a specific season and round"""
        logger.info(
            f"Fetching constructor standings for season {season}, round {round_num}"
        )

        # Get race information
        race_info = self.get_race_info(season, round_num)

        if not race_info:
            logger.warning(f"No race found for season {season}, round {round_num}")
            return

        race_name = race_info.get("raceName", "").lower().replace(" ", "-")

        # Create directories
        season_dir = self.base_dir / str(season)
        race_dir = season_dir / f"{race_name}"
        os.makedirs(race_dir, exist_ok=True)

        # Get constructor standings for this round
        standings = self.get_constructor_standings(season, round_num)

        if standings:
            standings_path = race_dir / "teamPoints.json"
            self.save_json(standings, standings_path)
            logger.info(
                f"Successfully saved constructor standings for {season} {race_name} (Round {round_num})"
            )
        else:
            logger.warning(
                f"No constructor standings found for {season}, round {round_num}"
            )


if __name__ == "__main__":
    logger.info("Starting data fetching for constructors...")
    fetcher = ConstructorStandingsFetcher(base_dir=".")
    # fetcher.fetch_standings_by_round(2025, 13)
    # fetcher.fetch_standings_by_round(2025, 14)
    # fetcher.fetch_standings_by_round(2025, 15)
    # fetcher.fetch_standings_by_round(2025, 16)
    # fetcher.fetch_standings_by_round(2025, 17)
    # fetcher.fetch_standings_by_round(2025, 18)
    # fetcher.fetch_standings_by_round(2025, 19)
    # fetcher.fetch_standings_by_round(2025, 20)
    # fetcher.fetch_standings_by_round(2025, 21)
    # fetcher.fetch_standings_by_round(2025, 22)
    fetcher.fetch_standings_by_round(2025, 23)
    # fetcher.fetch_standings_by_round(2025, 24)
