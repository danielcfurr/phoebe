import json
import pandas as pd
import numpy as np
from pathlib import Path
from pydub import AudioSegment

from birdnetlib import Recording
from birdnetlib.analyzer import Analyzer

BASE_DIR = Path(__file__).resolve().parent

SEGMENTS = 2


def main():
    """Main entry point for the script."""
    # May as well fail here first to avoid unproductive API calls
    analyzer = Analyzer()

    with open(BASE_DIR / "data" / "manifest.json") as f:
        manifest = json.load(f)

    raw_data_dir = BASE_DIR / 'data' / 'processed'
    for file in raw_data_dir.iterdir():
        if file.is_file():
            file.unlink()

    for recoding_id, data in manifest.items():
        file_in = BASE_DIR / data['local_raw']
        file_out = BASE_DIR / data['local_processed']
        print(f"Processing recording {recoding_id}, {file_in}, {file_out}")

        recording = analyze(analyzer, filepath=file_in, lat=data['lat'], lng=data['lon'], date=data['date'])

        scientific_name = data['gen'] + ' ' + data['sp']
        start, end, score = search_windows(recording, scientific_name=scientific_name, segments_per_window=SEGMENTS)
        process_mp3(file_in, start_sec=start, end_sec=end, output_path=file_out)


def analyze(analyzer: Analyzer, filepath: str, lat: float, lng: float, date: str) -> Recording:
    """Run the birdnet model against an audio file"""
    recording = Recording(
        analyzer, filepath,
        lat=lat, lon=lng, date=pd.to_datetime(date),
        return_all_detections=True,
    )

    recording.analyze()

    return recording


def search_windows(rec: Recording, scientific_name: str, segments_per_window) -> tuple:
    """Return the start time, end time, and score for the best window in a recording"""
    detections = pd.DataFrame(rec.detections)

    # Score each segment
    valence = pd.Series(detections['scientific_name'] == scientific_name).map({True: 1, False: -1})
    detections['scores'] = detections['confidence'] * valence
    segment_scores = detections.groupby(['start_time', 'end_time'])['scores'].sum()

    # Determine the expected segments and expand data frame to accommodate gaps in detection
    last_start, last_end = segment_scores.index[-1]
    segment_seconds = last_end - last_start
    expected_index = pd.Index([(i, i + segment_seconds) for i in range(0, int(last_end), int(segment_seconds))])
    segment_scores = segment_scores.reindex(expected_index).fillna(0)

    # Score each window
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
