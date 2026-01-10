import json
import os
import re
import time
from urllib.parse import quote

import requests


# Function to convert race name to slug
def slugify(race_name):
    # Convert to lowercase and replace spaces with hyphens
    slug = race_name.lower().replace(" ", "-")
    return slug


# Function to create directories
def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")


# Function to fetch data with rate limiting
def fetch_with_rate_limit(url):
    # Respect rate limits: 4 requests per second, 500 requests per hour
    time.sleep(0.3)  # Wait 0.25 seconds between requests (4 req/sec)

    response = requests.get(url)

    # Handle rate limiting
    if response.status_code == 429:
        print("Rate limit exceeded. Waiting 60 seconds before retrying...")
        time.sleep(60)
        return fetch_with_rate_limit(url)

    return response.json()


# Main function to fetch races and create folders
def main():
    # Base directory for storing race data
    base_dir = "."

    # Get list of seasons (you can adjust the range as needed)
    start_year = 2026
    end_year = 2026

    for year in range(start_year, end_year + 1):
        print(f"Processing year {year}...")

        # Create year directory
        year_dir = os.path.join(base_dir, str(year))
        create_directory(year_dir)

        # Fetch races for the year
        url = f"https://api.jolpi.ca/ergast/f1/{year}/races/"
        data = fetch_with_rate_limit(url)

        # Save year data to a JSON file in the year folder
        with open(os.path.join(year_dir, f"events.json"), "w") as f:
            json.dump(data, f, indent=2)

        # Process each race
        if (
            "MRData" in data
            and "RaceTable" in data["MRData"]
            and "Races" in data["MRData"]["RaceTable"]
        ):
            races = data["MRData"]["RaceTable"]["Races"]

            for race in races:
                race_name = race["raceName"]
                race_slug = slugify(race_name)

                # Create race directory with round number prefix for sorting
                race_dir = os.path.join(year_dir, f"{race_slug}")
                create_directory(race_dir)

                # Save race data to a JSON file
                with open(os.path.join(race_dir, "event_info.json"), "w") as f:
                    json.dump(race, f, indent=2)

                print(f"Processed: {year} - {race_name}")


if __name__ == "__main__":
    main()
    print("Done! All races have been processed and folders created.")
