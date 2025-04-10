"""
Module for interacting with the Xeno-Canto API to retrieve and process bird recordings.

This script performs the following tasks:
1. Queries the Xeno-Canto API to determine which bird recordings are available based on specified search criteria.
2. Selects a subset of these recordings to download or ensures that the necessary audio files are locally available.
3. Analyzes the downloaded recordings, identifying the best window of interest within each file.
"""

import requests
import pandas as pd
import numpy as np
from pathlib import Path
from pydub import AudioSegment

from birdnetlib import Recording
from birdnetlib.analyzer import Analyzer
from geopy.distance import distance

from dotenv import load_dotenv
import os

load_dotenv()  # Loads variables from .env into environment
API_KEY = os.getenv("XENOCANTO_API_KEY")

BASE_DIR = Path(__file__).resolve().parent

LATITUDE = 37
LONGITUDE = -122
RECORDINGS = 10
SEGMENTS = 4

QUERY = {
    'len': '>12',
    'q': 'A',
    'type': 'song'
}

BIRDS = [
    ('Sayornis nigricans', 'Black Phoebe'),
    ('Passer domesticus', 'House Sparrow'),
]


def main():
    """Main entry point for the script."""
    # May as well fail here first to avoid unproductive API calls
    analyzer = Analyzer()

    # Get an API response for each species
    manifest_holder = []
    for latin, common in BIRDS:
        print("Querying Xeno-Canto for", latin, 'aka', common)
        manifest_holder.append(get_manifest_for_target(scientific_name=latin, query=QUERY))

    # Assemble the responses into a data frame
    manifest = pd.concat(manifest_holder, axis=0)
    Path("data").mkdir(exist_ok=True)
    manifest.to_json(BASE_DIR / "data" / "manifest.json", orient="index", indent=2)

    # Download each "raw" .mp3 if not already present, select best window, and save to "processed"
    for idx, row in manifest.iterrows():
        file_in = BASE_DIR / row['local_raw']
        file_out = BASE_DIR / row['local_processed']
        print(f"Processing record {idx}, {file_in}, {file_out}")
        present = download_if_absent(url=row['file'], filepath=file_in)
        if present:
            recording = analyze(analyzer, filepath=file_in, lat=row['lat'], lng=row['lon'], date=row['date'])
            start, end, score = search_windows(recording, target=row['en'], segments_per_window=SEGMENTS)
            process_mp3(file_in, start_sec=start, end_sec=end, output_path=file_out)


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

    df = pd.DataFrame(recordings).set_index('id')
    df['km'] = df.apply(lambda row: distance((LATITUDE, LONGITUDE), (row['lat'], row['lon'])).km, axis=1)
    # penalty = df['q'].map({'A': 0, 'B': 500, 'C': 1000}).fillna(2000)  # TODO: Kept as reminder, deleted later
    # df['penalized_km'] = df['km'] + penalty
    df['local_raw'] = 'data/raw/' + df.index + '.mp3'
    df['local_processed'] = 'data/processed/' + df.index + '.mp3'

    return df.sort_values('km').head(RECORDINGS)


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


def analyze(analyzer: Analyzer, filepath: str, lat: float, lng: float, date: str) -> Recording:
    """Run the birdnet model against an audio file"""
    recording = Recording(
        analyzer, filepath,
        lat=lat, lon=lng, date=pd.to_datetime(date),
        return_all_detections=True,
    )

    recording.analyze()

    return recording


def search_windows(rec: Recording, target: str, segments_per_window) -> tuple:
    """Return the start time, end time, and score for the best window in a recording"""
    detections = pd.DataFrame(rec.detections).set_index(['start_time', 'end_time'])
    segment_seconds = detections.index[0][1]

    segment_scores = []
    for idx in detections.index.drop_duplicates():
        on_target = pd.Series(detections.loc[idx, 'common_name'] == target)
        valence = on_target.map({True: 1, False: -1})
        segment_scores.append(np.sum(valence * detections.loc[idx, 'confidence']))

    window_scores = [np.mean(segment_scores[i:(i + segments_per_window)]) for i in
                     range(len(segment_scores) - segments_per_window)]

    best = np.argmax(window_scores)
    start = best * segment_seconds
    end = (best + segments_per_window) * segment_seconds

    return start, end, window_scores[best]


def process_mp3(raw_path: str, start_sec: float, end_sec: float, output_path: str) -> None:
    """Clip an audio file saving a new copy"""
    audio = AudioSegment.from_mp3(raw_path)
    clipped = audio[start_sec * 1000:end_sec * 1000]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    clipped.export(path, format="mp3")

    return None


if __name__ == '__main__':
    main()
