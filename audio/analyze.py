import json
import numpy as np
import pandas as pd
from pathlib import Path
import librosa
from librosa.feature import rms
from birdnetlib import Recording
from birdnetlib.analyzer import Analyzer
import pyloudnorm

pd.set_option('future.no_silent_downcasting', True)

WINDOW_SIZE = 4  # Number of 3-second segments to scan for presence
SEGMENTS_PER_SECOND = 3  # As per birdnet model each segment is 3 seconds long
CLIP_SECONDS = 9  # Final desired clip duration

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "RAW"
MANIFEST_PATH = BASE_DIR / "data" / "manifest.csv"
ANALYSIS_PATH = BASE_DIR / "data" / "analysis.csv"


def main() -> None:
    analyzer = Analyzer()

    manifest = pd.read_csv(MANIFEST_PATH).set_index("id")
    manifest.index = manifest.index.astype(str)

    files = list(RAW_DIR.glob("*.mp3"))

    analysis_results = []
    for i, filepath in enumerate(files):
        print(i, "of", len(files))
        row = manifest.loc[filepath.stem]
        scientific_name = row["gen"] + " " + row["sp"]
        result = analyze_file(
            filepath,
            window_size=WINDOW_SIZE,
            analyzer=analyzer,
            scientific_name=scientific_name,
            lat=row["lat"],
            lon=row["lon"],
            date=row["date"]
        )
        result['id'] = filepath.stem
        analysis_results.append(result)

    analysis_df = pd.DataFrame(analysis_results)
    analysis_df.to_csv(ANALYSIS_PATH)


def analyze_file(filepath: Path, window_size: int, analyzer: Analyzer,
                 scientific_name: str, lat: float, lon: float, date: str) -> dict:
    """Run all analysis tasks for a given file"""
    result = find_presence(filepath, window_size=window_size, analyzer=analyzer,
                           scientific_name=scientific_name, lat=lat, lon=lon, date=date)
    data, rate = librosa.load(filepath)
    result['start'] = find_onset(data, rate=rate, start=result['presence_start'])
    result['end'] = result['start'] + CLIP_SECONDS
    s = int(result['start'] * rate)
    e = int(result['end'] * rate)
    result['floor_to_peak'] = floor_to_peak(data[s:e])
    result['loudness'] = get_loudness(data[s:e], rate=rate)
    return result


def score_presence(target_bool: pd.Series, other_bool: pd.Series) -> float:
    """Function to calculate a "presence" score for the bird of interest"""
    target_bool = pd.Series(target_bool, dtype=bool)
    other_bool = pd.Series(other_bool, dtype=bool)
    if any(other_bool):
        return 0.0
    elif target_bool.iloc[0]:
        return sum([float(t) / (i+1) for i, t in enumerate(target_bool)])
    else:
        return 0.0


def find_presence(filepath: Path, window_size: int, analyzer: Analyzer = None, scientific_name: str = None,
                  lat: float = None, lon: float = None, date: str = None) -> dict:
    """Find the window with the best presence score for a given file"""
    if analyzer is None:
        analyzer = Analyzer()

    recording = Recording(analyzer, filepath, return_all_detections=True, lat=lat, lon=lon, date=pd.to_datetime(date))
    recording.analyze()
    detections = pd.DataFrame(recording.detections)

    if scientific_name is None:
        counts = detections['scientific_name'].value_counts()
        scientific_name = counts.index[0]

    df = detections[['start_time', 'scientific_name']].copy()
    df['segment'] = df['start_time'].div(SEGMENTS_PER_SECOND).astype(int)
    df['target'] = df['scientific_name'] == scientific_name

    target_bool = df.groupby('segment')['target'].apply(lambda x: np.any(x))
    target_bool = target_bool.reindex(range(max(target_bool.index) + 1)).fillna(False)

    other_bool = df.groupby('segment')['target'].apply(lambda x: np.any(~x))
    other_bool = other_bool.reindex(range(max(other_bool.index) + 1)).fillna(False)

    presence_score = [
        score_presence(target_bool.iloc[i:i+window_size], other_bool.iloc[i:i+window_size])
        for i in range(len(target_bool))
    ]

    best = int(np.argmax(presence_score))

    result = {
        "scientific_name": scientific_name,
        "presence_start": best * SEGMENTS_PER_SECOND,
        "presence_end": (best + window_size) * SEGMENTS_PER_SECOND,
        "presence_score": presence_score[best],
    }

    return result


def find_onset(data: np.ndarray, rate: float, start: float, delta: float = .25) -> float:
    """Function to find the onset of audio near to a given starting second"""
    onsets = librosa.onset.onset_detect(y=data, sr=rate, backtrack=True, units='time', delta=delta)
    onsets = np.array(onsets)
    onsets = onsets[onsets < start + 3]
    onsets = onsets[onsets > start - 1]
    if not len(onsets):
        return start
    else:
        closest = np.argmin(np.abs(start - onsets))
        return float(onsets[closest])


def get_loudness(data: np.ndarray, rate: float):
    """Function to calculate loudness for a recording"""
    meter = pyloudnorm.Meter(rate)
    loudness = meter.integrated_loudness(data)
    return loudness


def floor_to_peak(data: np.ndarray):
    """Function to calculate the floor-to-peak value for a recording, representing amount of noise"""
    r = librosa.feature.rms(y=data).flatten()
    rolling_mean = pd.Series(r).rolling(window=10).mean().dropna()
    floor = rolling_mean.min()
    peak = rolling_mean.quantile(0.95)
    return floor / peak if peak > 0 else 0.0


if __name__ == "__main__":
    main()
