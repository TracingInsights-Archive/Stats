#!/usr/bin/env python3
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
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class PitstopsFetcher:
    def __init__(self, base_dir=".", season=None, round_num=None):
        """
        Initialize the PitstopsFetcher for a specific season and round.

        Args:
            base_dir: Base directory where race data is stored
            season: Season year to fetch pitstops for
            round_num: Round number to fetch pitstops for
        """
        self.base_dir = Path(base_dir)
        self.season = season
        self.round_num = round_num
        self.base_url = "https://api.jolpi.ca/ergast/f1"

        # Rate limiting parameters
        self.burst_limit = 4  # 4 requests per second
        self.last_request_time = 0

        # Ensure the base directory exists
        if not self.base_dir.exists():
            logger.error(f"Base directory {self.base_dir} does not exist")
            raise FileNotFoundError(f"Base directory {self.base_dir} does not exist")

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

    def get_race_info(self):
        """Get race information for the specified season and round"""
        events_file = self.base_dir / str(self.season) / "events.json"

        if not events_file.exists():
            logger.warning(f"Events file not found for season {self.season}")
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
                        if race["round"] == str(self.round_num):
                            return race
                    logger.warning(
                        f"Round {self.round_num} not found in season {self.season}"
                    )
                    return None
                logger.warning(f"Invalid events file format for season {self.season}")
                return None
        except Exception as e:
            logger.error(f"Error reading events file for season {self.season}: {e}")
            return None

    def get_race_folder_name(self, race):
        """Generate folder name for a race based on race name"""
        race_name = race["raceName"].lower().replace(" ", "-").replace("'", "")
        return race_name

    def fetch_pitstops_for_race(self):
        """
        Fetch all pitstops for the specified race using pagination

        Returns:
            Complete pitstops data for the race
        """
        limit = 100  # Maximum number of results per request
        offset = 0
        all_pitstops = []
        total_pitstops = None

        # Initial request
        url = f"{self.base_url}/{self.season}/{self.round_num}/pitstops.json?limit={limit}&offset={offset}"
        response_data = self.make_request(url)

        if not response_data:
            logger.error(
                f"Failed to fetch pitstops for {self.season} round {self.round_num}"
            )
            return None

        # Extract data from the response
        race_data = response_data["MRData"]
        total_pitstops = int(race_data["total"])

        # If there are no pitstops, return the empty response
        if total_pitstops == 0:
            logger.info(f"No pitstops found for {self.season} round {self.round_num}")
            return response_data

        # Add the first batch of pitstops
        if (
            "RaceTable" in race_data
            and "Races" in race_data["RaceTable"]
            and len(race_data["RaceTable"]["Races"]) > 0
        ):
            race = race_data["RaceTable"]["Races"][0]
            if "PitStops" in race:
                all_pitstops.extend(race["PitStops"])

        # Fetch remaining pitstops if needed
        while len(all_pitstops) < total_pitstops:
            offset += limit
            url = f"{self.base_url}/{self.season}/{self.round_num}/pitstops.json?limit={limit}&offset={offset}"
            response_data = self.make_request(url)

            if not response_data:
                logger.error(
                    f"Failed to fetch pitstops at offset {offset} for {self.season} round {self.round_num}"
                )
                break

            race_data = response_data["MRData"]
            if (
                "RaceTable" in race_data
                and "Races" in race_data["RaceTable"]
                and len(race_data["RaceTable"]["Races"]) > 0
            ):
                race = race_data["RaceTable"]["Races"][0]
                if "PitStops" in race:
                    all_pitstops.extend(race["PitStops"])

        # Reconstruct the complete response with all pitstops
        if (
            len(all_pitstops) > 0
            and "RaceTable" in response_data["MRData"]
            and "Races" in response_data["MRData"]["RaceTable"]
            and len(response_data["MRData"]["RaceTable"]["Races"]) > 0
        ):
            response_data["MRData"]["RaceTable"]["Races"][0]["PitStops"] = all_pitstops

        logger.info(
            f"Fetched {len(all_pitstops)} pitstops for {self.season} round {self.round_num}"
        )
        return response_data

    def run(self):
        """Run the pitstops fetcher for the specified season and round"""
        # Skip if season is before 2011 as pitstops data starts from 2011
        if self.season < 2011:
            logger.info(
                f"Skipping season {self.season} - pitstops data starts from 2011"
            )
            return

        race_info = self.get_race_info()
        if not race_info:
            logger.error(
                f"Could not find race information for {self.season} round {self.round_num}"
            )
            return

        race_name = race_info["raceName"]
        race_folder_name = self.get_race_folder_name(race_info)
        race_folder = self.base_dir / str(self.season) / race_folder_name

        # Create race folder if it doesn't exist
        if not race_folder.exists():
            logger.warning(f"Race folder {race_folder} does not exist, creating it")
            race_folder.mkdir(parents=True, exist_ok=True)

        pitstops_file = race_folder / "pitstops.json"

        logger.info(
            f"Fetching pitstops for {self.season} {race_name} (Round {self.round_num})"
        )
        pitstops_data = self.fetch_pitstops_for_race()

        if pitstops_data:
            with open(pitstops_file, "w") as f:
                json.dump(pitstops_data, f, indent=2)
            logger.info(f"Saved pitstops data to {pitstops_file}")
        else:
            logger.error(f"Failed to fetch pitstops for {self.season} {race_name}")


if __name__ == "__main__":
    # fetcher = PitstopsFetcher(base_dir=".", season=2025, round_num=13)
    # fetcher.run()
    # fetcher = PitstopsFetcher(base_dir=".", season=2025, round_num=14)
    # fetcher.run()
    # fetcher = PitstopsFetcher(base_dir=".", season=2025, round_num=15)
    # fetcher.run()
    # fetcher = PitstopsFetcher(base_dir=".", season=2025, round_num=16)
    # fetcher.run()
    # fetcher = PitstopsFetcher(base_dir=".", season=2025, round_num=17)
    # fetcher.run()
    # fetcher = PitstopsFetcher(base_dir=".", season=2025, round_num=18)
    # fetcher.run()
    # fetcher = PitstopsFetcher(base_dir=".", season=2025, round_num=19)
    # fetcher.run()
    # fetcher = PitstopsFetcher(base_dir=".", season=2025, round_num=20)
    # fetcher.run()
    # fetcher = PitstopsFetcher(base_dir=".", season=2025, round_num=21)
    # fetcher.run()
    fetcher = PitstopsFetcher(base_dir=".", season=2025, round_num=22)
    fetcher.run()
    fetcher = PitstopsFetcher(base_dir=".", season=2025, round_num=23)
    fetcher.run()
    fetcher = PitstopsFetcher(base_dir=".", season=2025, round_num=24)
    fetcher.run()
