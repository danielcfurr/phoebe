import requests
import pandas as pd
from pathlib import Path
from geopy.distance import distance


BASE_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = BASE_DIR / "data" / "manifest.csv"
RAW_PATH = BASE_DIR / "data" / "raw"

LATITUDE = 37
LONGITUDE = -122
RECORDINGS_PER_SPECIES = 40


def main():
    """Select the top recordings by species and download them"""
    manifest = pd.read_csv(MANIFEST_PATH, dtype={'id': str}, index_col='id')
    rankings = score_and_rank_recordings(manifest)
    index_for_downloading = rankings.index[rankings['rank'] <= RECORDINGS_PER_SPECIES]
    n = len(index_for_downloading)
    counter = 0
    for idx, row in manifest.loc[index_for_downloading].iterrows():
        counter += 1
        local_name = RAW_PATH / (idx + ".mp3")
        print(counter, "of", n, ":", local_name)
        try:
            download_if_absent(row['file'], local_name)
        except Exception as ex:
            print("Error downloading record_id", idx)
            print(ex)



def score_and_rank_recordings(manifest: pd.DataFrame) -> pd.DataFrame:
    """Score and rank order (by species) the files available for download"""
    # Use only rows having all necessary data points
    df = manifest[['gen', 'sp', 'length', 'lat', 'lon', 'q', 'smp']].copy()
    df = df.dropna()

    # Calculate values needed for scoring
    df['seconds'] = df['length'].apply(time_to_seconds)
    df['km'] = df.apply(lambda row: distance((LATITUDE, LONGITUDE), (row['lat'], row['lon'])).km, axis=1)

    # Apply some filter using hard limits
    df = df.loc[df['seconds'] >= 30]
    df = df.loc[df['seconds'] <= 300]
    df = df.loc[df['smp'] >= 40000]

    # Score and rank recordings available for download
    output = df[['gen', 'sp', 'km', 'seconds']].copy()
    output['quality_score'] = df['q'].apply(score_quality)
    output['seconds_score'] = df['seconds'].apply(score_seconds)
    output['distance_score'] = df['km'].apply(score_distance)
    output['final_score'] = output[['quality_score', 'seconds_score', 'distance_score']].sum(axis=1)
    output['rank'] = output.groupby(['gen', 'sp'])['final_score'].rank(method='first')

    return output


def time_to_seconds(x: str) -> int:
    """Convert a string like hh:mm:ss or mm:ss to an integer count of seconds"""
    splits = [int(s) for s in x.split(":")]
    if len(splits) == 2:
        splits = [0] + splits
    elif len(splits) != 3:
        raise ValueError("Expected hh:mm:ss or mm:ss")
    return sum([s*60**(2-i) for i, s in enumerate(splits)])


def score_seconds(x: int) -> float:
    """Score a recording duration on the range zero to one"""
    if x < 30:
        return 0.0
    elif x < 60:
        return (x / 60)**2
    else:
        return (60 / x)**1


def score_quality(x: str) -> float:
    """Score a recording for quality rating on the range zero to one"""
    if x == "A":
        return 1.0
    elif x == "B":
        return 0.8
    elif x == "C":
        return 0.6
    elif x == "E":
        return 0.0
    else:
        return 0.3


def score_distance(x: float) -> float:
    """Score a recording based on distance (closer is better) on the range zero to one"""
    if x > 5000:
        return 0.0
    else:
        return 1 - (x/5000)**2


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


if __name__ == '__main__':
    main()
