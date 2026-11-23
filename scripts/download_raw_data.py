""" This script downloads the raw CDC PLACES and EPA air quality files into data/raw/, exactly as each agency publishes them."""

from pathlib import Path

import requests

# Build paths from this file's location so the script works no matter which folder it's run from
project_root_folder = Path(__file__).resolve().parent.parent
raw_data_folder = project_root_folder / "data" / "raw"

# Each entry is the file name to save as, then the address to download it from
# PLACES 2025 release: county asthma estimates, based on 2023 survey data
# EPA annual files: yearly AQI summaries per county (median AQI, unhealthy days), but with county names only, no FIPS codes
# EPA daily files: one row per county per day, and they DO carry FIPS codes, so we use them to match county names to FIPS
# 2022 files are for the sensitivity check, since 2023 had heavy Canadian wildfire smoke
files_to_download = {
    "places_county_2025_release.csv": "https://data.cdc.gov/api/views/swc5-untb/rows.csv?accessType=DOWNLOAD",
    "annual_aqi_by_county_2023.zip": "https://aqs.epa.gov/aqsweb/airdata/annual_aqi_by_county_2023.zip",
    "annual_aqi_by_county_2022.zip": "https://aqs.epa.gov/aqsweb/airdata/annual_aqi_by_county_2022.zip",
    "daily_aqi_by_county_2023.zip": "https://aqs.epa.gov/aqsweb/airdata/daily_aqi_by_county_2023.zip",
    "daily_aqi_by_county_2022.zip": "https://aqs.epa.gov/aqsweb/airdata/daily_aqi_by_county_2022.zip",
    #Note: the 2023 SAIPE file is in Excel format, not CSV, so we need to use a different reader for it later 
    # Census SAIPE 2023: county poverty rate and median household income, same year as the asthma survey; one file covers every state and county
    "saipe_2023_state_and_county.xls": "https://www2.census.gov/programs-surveys/saipe/datasets/2023/2023-state-and-county/est23all.xls",
}


def download_file(download_address, output_file_path):
    # Save under a temporary name first, so a download that breaks halfway is never mistaken for a complete file
    temporary_file_path = output_file_path.with_name(output_file_path.name + ".partial")
    # stream=True pulls the file down in pieces, so a large file never has to fit in memory all at once
    with requests.get(download_address, stream=True, timeout=300) as download_response:
        # Stop with a clear error if the server refuses, instead of quietly saving an error page as if it were data
        download_response.raise_for_status()
        with open(temporary_file_path, "wb") as output_file:
            for file_piece in download_response.iter_content(chunk_size=1024 * 1024):
                output_file.write(file_piece)
    # Only rename to the real name once every piece has been written
    temporary_file_path.replace(output_file_path)


def main():
    raw_data_folder.mkdir(parents=True, exist_ok=True)
    for output_file_name, download_address in files_to_download.items():
        output_file_path = raw_data_folder / output_file_name
        # Skip files that are already here, so re-running the pipeline doesn't download everything again
        if output_file_path.exists():
            print(f"Already have {output_file_name}, skipping")
            continue
        print(f"Downloading {output_file_name} ...")
        download_file(download_address, output_file_path)
        file_size_in_megabytes = output_file_path.stat().st_size / 1_000_000
        print(f"  Saved {output_file_name} ({file_size_in_megabytes:.1f} MB)")


if __name__ == "__main__":
    main()