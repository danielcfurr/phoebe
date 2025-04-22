import json
import pandas as pd
from pathlib import Path
from pydub import AudioSegment
from collections import defaultdict


BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MANIFEST_PATH = BASE_DIR / "data" / "manifest.csv"
ANALYSIS_PATH = BASE_DIR / "data" / "analysis.csv"
APP_DATA_PATH = BASE_DIR / "data" / "app_data.json"


def main():
    manifest = pd.read_csv(MANIFEST_PATH, index_col="id", dtype={"id": str})
    analysis = pd.read_csv(ANALYSIS_PATH, index_col="id", dtype={"id": str})
    best_recording_ids = get_best_recording_ids(analysis)

    recordings = {}
    n = len(best_recording_ids)
    for i, idx in enumerate(best_recording_ids):
        print(i + 1, "of", n, ":", idx)
        analysis_row = analysis.loc[idx]
        manifest_row = manifest.loc[idx]
        file_name = idx + ".mp3"

        # Try to clip the audio file
        try:
            clip_mp3(
                input_path=RAW_DIR / file_name,
                output_path=PROCESSED_DIR / file_name,
                start_sec=analysis_row["start"],
                end_sec=analysis_row["end"]
            )
        except Exception as ex:
            print("Error with", idx)
            print(ex)
            continue

        # Test the audio file may be loaded and add metadata to dictionary or delete file
        if validate_mp3(PROCESSED_DIR / file_name):
            recordings[idx] = {
                "scientific_name": analysis_row["scientific_name"],
                "common_name": manifest_row["en"],
                "author": manifest_row["rec"],
                "license": manifest_row["lic"],
                "url": manifest_row["url"],
                "file_name": idx + ".mp3"
            }
        else:
            Path(PROCESSED_DIR / file_name).unlink()

    lookup = defaultdict(list)
    for record_id, record_data in recordings.items():
        lookup[record_data['scientific_name']].append(record_id)

    app_data = {"lookup": lookup, "recordings": recordings}
    with open(APP_DATA_PATH, "w") as file:
        json.dump(app_data, file,  indent=4)


def get_best_recording_ids(analysis: pd.DataFrame) -> list:
    return (
        analysis
        .sort_values(by=['presence_score', 'floor_to_peak'], ascending=[False, True])
        .groupby('scientific_name')
        .head(20)
        .sort_values(by=['floor_to_peak'], ascending=[True])
        .groupby('scientific_name')
        .head(10)
        .index
        .tolist()
    )


def clip_mp3(input_path: str, output_path: str, start_sec: float, end_sec: float) -> None:
    """Clip an audio file saving a new copy"""
    audio = AudioSegment.from_mp3(input_path)
    clipped = audio[start_sec * 1000:end_sec * 1000]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    clipped.export(path, format="mp3")


def validate_mp3(file_path):
    try:
        _ = AudioSegment.from_file(file_path)
        return True
    except Exception as e:
        print("Validation error with", file_path, ":", e)
        return False


if __name__ == '__main__':
    main()
