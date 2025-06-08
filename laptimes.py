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
    handlers=[logging.FileHandler("laptimes_fetch.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.jolpi.ca/ergast/f1"
LIMIT = 100  # Number of records per request
RATE_LIMIT_BURST = 4  # Max requests per second
RATE_LIMIT_SUSTAINED = 500  # Max requests per hour


def fetch_laptimes(year, round_num):
    """Fetch all lap times for a specific race with pagination."""
    all_data = None
    offset = 0
    total_records = None

    while total_records is None or offset < total_records:
        url = f"{BASE_URL}/{year}/{round_num}/laps.json?limit={LIMIT}&offset={offset}"
        logger.info(f"Fetching data from: {url}")

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            # Initialize all_data with the first response
            if all_data is None:
                all_data = data
                total_records = int(data["MRData"]["total"])
                logger.info(f"Total records to fetch: {total_records}")
            else:
                # Append new lap data to existing data
                if "Laps" in data["MRData"]["RaceTable"]["Races"][0]:
                    all_data["MRData"]["RaceTable"]["Races"][0]["Laps"].extend(
                        data["MRData"]["RaceTable"]["Races"][0]["Laps"]
                    )

            offset += LIMIT

            # Respect rate limits
            time.sleep(1 / RATE_LIMIT_BURST)  # Ensure we don't exceed burst limit

        except requests.exceptions.RequestException as e:
            if hasattr(e.response, "status_code") and e.response.status_code == 429:
                logger.warning("Rate limit exceeded. Waiting for 60 seconds...")
                time.sleep(60)  # Wait longer if we hit rate limit
                continue
            logger.error(f"Error fetching data: {e}")
            return None

    return all_data


def save_laptimes(data, year, round_num):
    """Save lap times data to laptimes.json in the appropriate folder."""
    # Get race name from the data
    race_name = (
        data["MRData"]["RaceTable"]["Races"][0]["raceName"].lower().replace(" ", "-")
    )

    # Create directory structure
    year_path = Path(str(year))
    race_folder = year_path / race_name

    # Create directories if they don't exist
    race_folder.mkdir(parents=True, exist_ok=True)

    # Save the data
    output_file = race_folder / "laptimes.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved lap times data to {output_file}")


def main(year, round_num):
    """Main function to fetch lap times for a specific round in a specific year."""

    logger.info(f"Fetching lap times for year {year}, round {round_num}")

    # Fetch lap times data
    lap_data = fetch_laptimes(year, round_num)

    if lap_data:
        # Save the data
        save_laptimes(lap_data, year, round_num)
        logger.info(
            f"Successfully fetched and saved lap times for year {year}, round {round_num}"
        )
    else:
        logger.error(f"Failed to fetch lap times for year {year}, round {round_num}")


if __name__ == "__main__":
    main(2025, 8)
    main(2025, 9)
