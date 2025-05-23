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
LICENSE_MARKDOWN_PATH = BASE_DIR / "data" / "licenses.md"
RECORDINGS_PER_BIRD = 10


def main():
    manifest = pd.read_csv(MANIFEST_PATH, index_col="id", dtype={"id": str})
    analysis = pd.read_csv(ANALYSIS_PATH, index_col="id", dtype={"id": str})
    analysis = sort_analysis_dataframe(analysis)

    app_data = defaultdict(list)
    for sn in analysis['scientific_name'].drop_duplicates():
        counter = 0
        for idx, analysis_row in analysis.loc[analysis['scientific_name'] == sn].iterrows():
            manifest_row = manifest.loc[idx]
            file_name = idx + ".mp3"
            input_path = RAW_DIR / file_name
            output_path = PROCESSED_DIR / file_name

            try:
                # Clip the audio file and write
                clip_mp3(
                    input_path=input_path,
                    output_path=output_path,
                    start_sec=analysis_row["start"],
                    end_sec=analysis_row["end"]
                )
                # Test file can be loaded and has appropriate duration
                validate_audio_file(output_path, analysis_row["end"] - analysis_row["start"])
                # Record metadata
                app_data[sn].append({
                    "recording_id": idx,
                    "scientific_name": analysis_row["scientific_name"],
                    "common_name": manifest_row["en"],
                    "author": manifest_row["rec"],
                    "license": manifest_row["lic"],
                    "url": manifest_row["url"],
                    "file_name": idx + ".mp3",
                    "start_sec": analysis_row["start"],
                    "end_sec": analysis_row["end"],
                })
                print("Processed", idx, sn)
                counter += 1
            except Exception as ex:
                output_path.unlink(missing_ok=True)
                print("Error processing", idx, sn, ":", ex)

            if counter >= RECORDINGS_PER_BIRD:
                break

    with open(APP_DATA_PATH, "w") as file:
        json.dump(app_data, file,  indent=4)

    write_license_markdown(app_data)


def sort_analysis_dataframe(analysis: pd.DataFrame) -> pd.DataFrame:
    """Sort dataframe based on goodness of recording segments"""
    score = (1-analysis["floor_to_peak"])**2 * analysis["presence_score"]
    new_index = score.sort_values(ascending=False).index
    return analysis.loc[new_index]


def clip_mp3(input_path: str, output_path: str, start_sec: float, end_sec: float) -> None:
    """Clip an audio file saving a new copy"""
    audio = AudioSegment.from_mp3(input_path)
    clipped = audio[start_sec * 1000:end_sec * 1000]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    clipped.export(path, format="mp3")


def validate_audio_file(path: Path, expected_seconds: float):
    """Test that audio file has approximately the expected duration"""
    audio = AudioSegment.from_file(path)
    if abs(audio.duration_seconds - expected_seconds) > expected_seconds * .1:
        raise ValueError(
            f"Audio duration of {audio.duration_seconds} differs substantially from expected {expected_seconds}.")


def write_license_markdown(app_data: dict):
    """Write a markdown file listing license info for the processed audio files"""
    recordings = []
    for _, recordings_for_scientific_name in app_data.items():
        recordings += recordings_for_scientific_name

    df = pd.DataFrame(recordings).set_index('file_name')[['author', 'url', 'license']].sort_index()

    markdown = f"""
    # Audio file licenses

    All audio files in [processed/](processed) are clipped from files available under Creative Common licenses.
    The creator and license for each file is provided below.

    {df.to_markdown()}
    """

    # Cannot use dedent because only first line of table will be indented
    no_indent = "\n".join(line.lstrip() for line in markdown.splitlines())

    with open(LICENSE_MARKDOWN_PATH, "w") as file:
        file.write(no_indent)


if __name__ == '__main__':
    main()
