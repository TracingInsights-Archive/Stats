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
    handlers=[logging.FileHandler("sprint_results_fetch.log"), logging.StreamHandler()],
)

logger = logging.getLogger("sprint_results_fetcher")


class SprintResultsFetcher:
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
        """Get race information for the specified season and round"""
        events_file = self.base_dir / str(season) / "events.json"

        if not events_file.exists():
            logger.warning(f"Events file not found for season {season}")
            # Try to fetch from API
            url = f"{self.base_url}/{season}/races.json"
            data = self.make_request(url)
            if (
                data
                and "MRData" in data
                and "RaceTable" in data["MRData"]
                and "Races" in data["MRData"]["RaceTable"]
            ):
                races = data["MRData"]["RaceTable"]["Races"]
                for race in races:
                    if race["round"] == str(round_num):
                        return race
                logger.warning(f"Round {round_num} not found in season {season}")
                return None
            return None

        try:
            with open(events_file, "r") as f:
                data = json.load(f)
                if (
                    "MRData" in data
                    and "RaceTable" in data["MRData"]
                    and "Races" in data["MRData"]["RaceTable"]
                ):
                    races = data["MRData"]["RaceTable"]["Races"]
                    for race in races:
                        if race["round"] == str(round_num):
                            return race
                    logger.warning(f"Round {round_num} not found in season {season}")
                    return None
                logger.warning(f"Invalid events file format for season {season}")
                return None
        except Exception as e:
            logger.error(f"Error reading events file for season {season}: {e}")
            return None

    def has_sprint(self, race):
        """Check if a race has a sprint event"""
        return "Sprint" in race

    def get_sprint_results(self, season, round_num):
        """Get sprint results for a specific season and round"""
        url = f"{self.base_url}/{season}/{round_num}/sprint.json"
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

    def fetch_sprint_for_round(self, season, round_num):
        """Fetch sprint results for a specific season and round"""
        logger.info(f"Fetching sprint results for season {season}, round {round_num}")

        # Create season directory
        season_dir = self.base_dir / str(season)
        os.makedirs(season_dir, exist_ok=True)

        # Get race information
        race = self.get_race_info(season, round_num)

        if not race:
            logger.warning(
                f"Race information not found for season {season}, round {round_num}"
            )
            return False

        race_name = self.get_race_folder_name(race)

        # Check if race has a sprint
        if not self.has_sprint(race):
            logger.warning(
                f"No sprint for {race_name} (Round {round_num}) in season {season}"
            )
            return False

        logger.info(f"Found sprint race: {race_name} (Round {round_num})")

        # Create race directory
        race_dir = season_dir / race_name
        os.makedirs(race_dir, exist_ok=True)

        # Get sprint results
        sprint_results = self.get_sprint_results(season, round_num)

        if sprint_results:
            sprint_results_path = race_dir / "sprint_results.json"
            return self.save_json(sprint_results, sprint_results_path)
        else:
            logger.warning(
                f"No sprint results found for {race_name} (Round {round_num}) in season {season}"
            )
            return False


if __name__ == "__main__":
    # Configuration - modify these values directly
    season = 2025  # The season to fetch
    round_num = 6  # The round number to fetch

    # Base directory where season folders are located
    base_dir = "."

    logger.info(
        f"Starting sprint results fetcher for season {season}, round {round_num}"
    )

    fetcher = SprintResultsFetcher(base_dir=base_dir)
    success = fetcher.fetch_sprint_for_round(season, round_num)

    if success:
        logger.info(
            f"Successfully fetched sprint results for season {season}, round {round_num}"
        )
    else:
        logger.warning(
            f"Failed to fetch sprint results for season {season}, round {round_num}"
        )
