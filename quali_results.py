import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("qualifying_results_fetch.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("qualifying_results_fetcher")


class QualifyingResultsFetcher:
    def __init__(self, base_dir="."):
        self.base_dir = Path(base_dir)
        self.base_url = "https://api.jolpi.ca/ergast/f1"
        # Rate limits
        self.burst_limit = 4  # requests per second
        self.last_request_time = 0

    def get_race_folder_name(self, race):
        """Convert race name to folder name format"""
        return race["raceName"].lower().replace(" ", "-")

    def make_request(self, url):
        """Make a request to the API with rate limiting"""
        # Ensure we don't exceed burst limit
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < (1 / self.burst_limit):
            sleep_time = (1 / self.burst_limit) - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        logger.debug(f"Making request to: {url}")
        response = requests.get(url)
        self.last_request_time = time.time()

        if response.status_code == 429:
            logger.warning("Rate limit exceeded. Waiting 30 seconds before retrying.")
            time.sleep(30)
            return self.make_request(url)

        if response.status_code != 200:
            logger.error(
                f"Error fetching data: {response.status_code} - {response.text}"
            )
            return None

        return response.json()

    def get_race_info(self, season, round_num):
        """Get race information for a specific season and round"""
        url = f"{self.base_url}/{season}/{round_num}.json"
        data = self.make_request(url)
        if (
            data
            and "MRData" in data
            and "RaceTable" in data["MRData"]
            and "Races" in data["MRData"]["RaceTable"]
            and len(data["MRData"]["RaceTable"]["Races"]) > 0
        ):
            return data["MRData"]["RaceTable"]["Races"][0]
        return None

    def get_qualifying_results(self, season, round_num):
        """Get qualifying results for a specific season and round"""
        url = f"{self.base_url}/{season}/{round_num}/qualifying.json"
        return self.make_request(url)

    def save_json(self, data, filepath):
        """Save data as JSON to the specified filepath"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved data to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving data to {filepath}: {e}")
            return False

    def fetch_round(self, season, round_num):
        """Fetch qualifying results for a specific season and round"""
        logger.info(
            f"Fetching qualifying results for season {season}, round {round_num}"
        )

        # Create season directory
        season_dir = self.base_dir / str(season)
        os.makedirs(season_dir, exist_ok=True)

        # Get race information
        race_info = self.get_race_info(season, round_num)

        if not race_info:
            logger.warning(f"No race found for season {season}, round {round_num}")
            return

        race_name = self.get_race_folder_name(race_info)

        # Create race directory
        race_dir = season_dir / race_name
        os.makedirs(race_dir, exist_ok=True)

        # Get qualifying results
        qualifying_results = self.get_qualifying_results(season, round_num)

        if qualifying_results:
            qualifying_results_path = race_dir / "quali_results.json"
            self.save_json(qualifying_results, qualifying_results_path)
            logger.info(
                f"Successfully fetched qualifying results for {season} {race_name}"
            )
        else:
            logger.warning(f"No qualifying results found for {season} {race_name}")


if __name__ == "__main__":
    fetcher = QualifyingResultsFetcher(base_dir=".")
    # fetcher.fetch_round(2025, 13)
    # fetcher.fetch_round(2025, 14)
    # fetcher.fetch_round(2025, 15)
    # fetcher.fetch_round(2025, 16)
    # fetcher.fetch_round(2025, 17)
    # fetcher.fetch_round(2025, 18)
    # fetcher.fetch_round(2025, 19)
    fetcher.fetch_round(2025, 20)
    # fetcher.fetch_round(2025, 21)
    # fetcher.fetch_round(2025, 22)
    # fetcher.fetch_round(2025, 23)
    # fetcher.fetch_round(2025, 24)
    logger.info("Qualifying results fetching completed")
