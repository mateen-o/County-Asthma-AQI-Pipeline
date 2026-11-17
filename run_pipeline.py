"""This runs the whole data pipeline in order: it downloads, loads, cleans, and validates the data. One command rebuilds the database from nothing."""

import subprocess
import sys
from pathlib import Path

# Build paths from this file's location so the pipeline runs the same no matter which folder it's started from
project_root_folder = Path(__file__).resolve().parent

# Order matters: each script needs what the one before it made
pipeline_scripts = ["download_raw_data.py", "load_raw_data.py", "build_clean_tables.py", "validating_database.py"]


def main():
    for script_name in pipeline_scripts:
        print(f"\n===== {script_name} =====", flush=True)
        # sys.executable is the Python running this file, so every step uses the same conda environment
        script_result = subprocess.run([sys.executable, str(project_root_folder / "scripts" / script_name)])
        # Stop at the first failure, so a later step never runs on top of a broken earlier one
        if script_result.returncode != 0:
            print(f"\nPipeline stopped: {script_name} failed")
            sys.exit(script_result.returncode)
    print("\nPipeline finished: database rebuilt and all validation checks passed")


if __name__ == "__main__":
    main()