import numpy as np
import pandas as pd
from pathlib import Path
import librosa
from librosa.feature import rms
from birdnetlib import Recording
from birdnetlib.analyzer import Analyzer
import pyloudnorm

pd.set_option('future.no_silent_downcasting', True)


BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
MANIFEST_PATH = BASE_DIR / "data" / "manifest.csv"
ANALYSIS_PATH = BASE_DIR / "data" / "analysis.csv"

# Settings for birdnet model and presence analysis
WEIGHTS = np.square(np.linspace(2, 1, 4))
OVERLAP = 1  # Overlap is a misnomer. Value of one means that three seconds frames have two seconds of overlap.
MIN_CONF = 0


def main() -> None:
    """Analyze all .mp3 files in the raw data directory and write a .csv of the results"""
    analyzer = Analyzer()

    manifest = pd.read_csv(MANIFEST_PATH, dtype={'id': str}, index_col='id')

    files = list(RAW_DIR.glob("*.mp3"))
    n = len(files)

    analysis_results = []
    for i, filepath in enumerate(files):
        print(i + 1, "of", n, ":", filepath)
        row = manifest.loc[filepath.stem]
        scientific_name = row["gen"] + " " + row["sp"]
        try:
            result = analyze_file(
                filepath,
                weights=WEIGHTS,
                analyzer=analyzer,
                scientific_name=scientific_name,
                lat=row["lat"],
                lon=row["lon"],
                date=pd.to_datetime(row["date"]),
                overlap=OVERLAP,
                min_conf=MIN_CONF,
            )
            result['id'] = filepath.stem
            analysis_results.append(result)
        except Exception as ex:
            print("Error processing", filepath)
            print(ex)

    analysis_df = pd.DataFrame(analysis_results).set_index('id')
    analysis_df.to_csv(ANALYSIS_PATH)


def analyze_file(filepath: Path, analyzer: Analyzer, scientific_name: str, weights: np.ndarray, **kwargs) -> dict:
    """Run all analysis tasks for a given file"""
    presence_start, presence_end, df = analyze_presence(
        analyzer,
        filepath=filepath,
        scientific_name=scientific_name,
        weights=weights,
        **kwargs
    )

    # Start a dictionary of results to return
    result = {
        "scientific_name": scientific_name,
        "presence_start": presence_start,
        "presence_end": presence_end,
        "presence_score": df['score'].max(),
    }

    data, rate = librosa.load(filepath)

    # Find an onset near to `presence_start` and add to dictionary
    result['start'] = find_onset(data, rate=rate, start=result['presence_start'])
    duration = presence_end - presence_start
    result['end'] = result['start'] + duration

    # Reduce audio data to a clip
    s = int(result['start'] * rate)
    e = int(result['end'] * rate)
    clip = data[s:e]

    # Add metrics for the clip to the dictionary
    result['floor_to_peak'] = floor_to_peak(clip)
    result['loudness'] = get_loudness(clip, rate=rate)

    return result


def analyze_presence(analyzer: Analyzer, filepath: Path, scientific_name: str, weights: np.ndarray, **kwargs) -> tuple:
    """Analyze an audio file for presence of target bird, identifying the best segment"""
    if analyzer is None:
        analyzer = Analyzer()

    recording = Recording(analyzer, filepath, **kwargs)
    recording.analyze()

    # Make dataframe with one row per frame summarizing presence of target bird and off target birds
    detections = pd.DataFrame(recording.detections)
    grouper = detections.groupby("start_time")
    on_target = grouper.apply(
        lambda grp: sum(grp['confidence'] * pd.Series(grp['scientific_name'] == scientific_name).astype(float)),
        include_groups=False
    )
    off_target = grouper.apply(
        lambda grp: sum(grp['confidence'] * pd.Series(grp['scientific_name'] != scientific_name).astype(float)),
        include_groups=False
    )
    aggregate = pd.DataFrame({"on_target": on_target, "off_target": off_target})
    aggregate['delta'] = aggregate["on_target"] - aggregate["off_target"]

    # Expand that dataframe to include any missing time points / frames
    last_start = detections["start_time"].iloc[-1]
    increment = 3 if recording.overlap == 0 else recording.overlap  # overlap
    expected_starts = np.arange(0, last_start + increment, increment)
    aggregate = aggregate.reindex(expected_starts).fillna(0)

    # Get a weighted average score across a number of frames
    n_frames = len(weights)
    score_holder = [pd.NA] * len(aggregate)
    for i in range(len(aggregate) - n_frames + 1):
        subset = aggregate.iloc[i:i + n_frames]
        weighted_mean = np.average(subset["on_target"] - subset["off_target"], weights=weights)
        score_holder[i] = weighted_mean

    # Find the best start and end times
    aggregate['score'] = score_holder
    best = aggregate['score'].argmax()
    best_start_time = aggregate.index[best]
    best_end_time = aggregate.index[best+n_frames] + 3

    return best_start_time, best_end_time, aggregate


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
