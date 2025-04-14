from typing import List
import requests
import pandas as pd
from pathlib import Path
from geopy.distance import distance
from dotenv import load_dotenv
import os

load_dotenv()  # Loads variables from .env into environment
API_KEY = os.getenv("XENOCANTO_API_KEY")

BASE_DIR = Path(__file__).resolve().parent

LATITUDE = 37
LONGITUDE = -122
RECORDINGS = 10
SEGMENTS = 2

QUERY = {
    'len': '>30',
    'q': 'A',
    'type': 'song'
}

with open(BASE_DIR / "scientific_names.txt") as f:
    SCIENTIFIC_NAMES = f.read().splitlines()


def main():
    """Main entry point for the script."""
    # Get an API response for each species
    manifest_holder = []
    for scientific_name in SCIENTIFIC_NAMES:
        print("Querying Xeno-Canto for", scientific_name)
        manifest_holder.append(get_manifest_for_target(scientific_name=scientific_name, query=QUERY))

    # Assemble the responses into a data frame
    manifest = pd.concat(manifest_holder, axis=0)
    Path("data").mkdir(exist_ok=True)
    manifest.to_json(BASE_DIR / "data" / "manifest.json", orient="index", indent=2)

    # Download each "raw" .mp3 if not already present, select best window, and save to "processed"
    for idx, row in manifest.iterrows():
        file_in = BASE_DIR / row['local_raw']
        print(f"Retrieving recording {idx}, {file_in}")
        download_if_absent(url=row['file'], filepath=file_in)

    # Remove unused mp3s
    prune_mp3s(BASE_DIR / "data" / "raw", expected=manifest['local_raw'].tolist())


def get_manifest_for_target(scientific_name: str, per_page=500, query=None) -> pd.DataFrame:
    """Get a dataframe of audio files for target bird from Xeno-Canto"""
    base_url = "https://xeno-canto.org/api/3/recordings"

    if query is None:
        query = {}

    query['sp'] = scientific_name

    query_string = ' '.join([f'{key}:"{item}"' for key, item in query.items()])

    response = requests.get(base_url, params={"query": query_string, "key": API_KEY, "per_page": per_page})

    # Check for success
    if response.status_code == 200:
        data = response.json()
    else:
        print(f"Request failed with status code {response.status_code}")
        return pd.DataFrame()

    recordings = data.pop('recordings')
    print(data)

    if len(data):
        df = pd.DataFrame(recordings).set_index('id')
        df['km'] = df.apply(lambda row: distance((LATITUDE, LONGITUDE), (row['lat'], row['lon'])).km, axis=1)
        # penalty = df['q'].map({'A': 0, 'B': 500, 'C': 1000}).fillna(2000)  # TODO: Kept as reminder, deleted later
        # df['penalized_km'] = df['km'] + penalty
        df['local_raw'] = 'data/raw/' + df.index + '.mp3'
        df['local_processed'] = 'data/processed/' + df.index + '.mp3'
        return df.sort_values('km').head(RECORDINGS)
    else:
        return pd.DataFrame(index=pd.Series(name='id'))


def download_if_absent(url: str, filepath: str) -> bool:
    """Download file if absent, returning True if successful or file already present"""
    path = Path(filepath)
    if path.exists():
        return True

    response = requests.get(url)

    if response.status_code != 200:
        print(f"Failed download to {path}. Status code: {response.status_code}")
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(response.content)

    return True


def prune_mp3s(directory: Path, expected: List[Path | str]) -> None:
    """Remove "unexpected" .mp3 files from a directory"""
    directory = directory.resolve()
    expected = [Path(e).resolve() for e in expected]

    for fp in directory.glob("*.mp3"):
        if fp in expected:
            pass
        else:
            fp.unlink()
            print('Pruned', str(fp))


if __name__ == '__main__':
    main()
