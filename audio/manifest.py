import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("XENOCANTO_API_KEY")

BASE_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = BASE_DIR / "data" / "manifest.csv"
SCIENTIFIC_NAMES_PATH = BASE_DIR / "scientific_names.txt"


def main():
    with open(SCIENTIFIC_NAMES_PATH) as f:
        scientific_names = f.read().splitlines()
    manifest_df = manifest_xenocanto_all(scientific_names)
    manifest_df.to_csv(MANIFEST_PATH)
    print("Wrote manifest:", MANIFEST_PATH)


def manifest_xenocanto_all(scientific_names: list) -> pd.DataFrame:
    """Function to get records for all selected species"""
    manifest_list = []
    for name in scientific_names:
        manifest_list.append(manifest_xenocanto_one_species(name, key=API_KEY))

    manifest_df = pd.concat(manifest_list, axis=0)

    return manifest_df


def manifest_xenocanto_one_species(scientific_name: str, key: str) -> pd.DataFrame:
    """Function to get all matching records for a species with pagination"""
    query_params = [("sp", scientific_name)]

    print(scientific_name, "first request")
    first_response = query_xenocanto(query_params, key=key, page=1)
    first_data = first_response.json()
    pages = first_data["numPages"]

    recording_list = [first_data["recordings"]]
    for p in range(2, pages + 1):
        print(scientific_name, "page", p, "of", pages)
        response = query_xenocanto(query_params, key=key, page=p)
        additional_recordings = response.json()['recordings']
        recording_list.append(additional_recordings)

    df = pd.concat(
        [pd.DataFrame(data) for data in recording_list],
        axis=0
    )

    df = df.set_index("id")

    return df


def query_xenocanto(query_params: list, key: str, per_page: int = 100, page: int = 1):
    """Function to make request to Xeno-Canto"""
    base_url = "https://xeno-canto.org/api/3/recordings"
    query_string = ' '.join([f'{key}:"{item}"' for key, item in query_params])
    return requests.get(base_url, params={"query": query_string, "key": key, "per_page": per_page, "page": page})


if __name__ == "__main__":
    main()
