import json
import streamlit as st
from pathlib import Path, PurePosixPath
import random
import argparse


AUDIO_DIR = Path().resolve() / "audio" / "data" / "processed"
APP_DATA_PATH = Path().resolve() / "audio" / "data" / "app_data.json"
RATINGS_LOG_PATH = Path().resolve() / "ratings.json"
BIRD_IMAGE_DATA_PATH = Path().resolve() / "images" / "data" / "bird_images.jsonl"
BIRD_IMAGE_DIR = Path().resolve() / "images" / "data" / "birds"

with open(APP_DATA_PATH) as file:
    APP_DATA = json.load(file)

BIRDS = list(APP_DATA.keys())

with open(BIRD_IMAGE_DATA_PATH, "r") as file:
    BIRD_IMAGE_DATA = [json.loads(line) for line in file]
    BIRD_IMAGE_DATA = {x["scientific_name"]: x for x in BIRD_IMAGE_DATA}

if RATINGS_LOG_PATH.exists():
    with open(RATINGS_LOG_PATH, "r") as file:
        ratings = json.load(file)
else:
    ratings = {}
    for bird, records in APP_DATA.items():
        for record in records:
            ratings[record["recording_id"]] = {
                "start_sec": record["start_sec"],
                "end_sec": record["end_sec"],
                "Noise": None,
                "Presence": None,
                "Multiple": None,
            }


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rate",
        action="store_true",
        help="Enable rating mode"
    )
    args, _ = parser.parse_known_args()
    return args


def generate_item():
    odd_bird, paired_bird = random.sample(BIRDS, k=2)
    odd_list = random.sample(APP_DATA[odd_bird], k=1)
    paired_list = random.sample(APP_DATA[paired_bird], k=2)
    complete_list = odd_list + paired_list
    order = random.sample(range(3), k=3)
    ordered_list = [complete_list[j] for j in order]
    key = order.index(0)
    return ordered_list, key


def audio_widget(record):
    file_path = AUDIO_DIR / record["file_name"]
    audio_file = open(file_path, "rb")
    audio_bytes = audio_file.read()
    st.audio(audio_bytes, format="audio/mp3")


def credit(record, reveal=True):
    if reveal:
        recording_lic_text, recording_lic_number = PurePosixPath(record["license"]).parts[-2:]
        scientific_name = record["scientific_name"]

        image = BIRD_IMAGE_DATA[scientific_name]
        image_lic_text, image_lic_number = PurePosixPath(image["license_url"]).parts[-3:-1]

        st.write(f"""
            **{record["common_name"]}**
            (*{scientific_name}*) <br>
            <span style="color:gray;">
            [Audio]({record["url"]}): 
            {record["author"]} 
            ([CC {recording_lic_text} {recording_lic_number}]({record["license"]})) <br>
            [Photo]({image["url"]}): 
            {image["author"]} 
            ([CC {image_lic_text} {image_lic_number}]({image["license_url"]}))
            </span>
        """, unsafe_allow_html=True)

    else:

        st.write("""
            *Secret bird* <br>
            <span style="color:gray;">
            Audio: *???* <br>
            Photo: *???* <br>
            </span>
        """, unsafe_allow_html=True)


def rating_widget(record_id, label, options):
    current_selection = st.session_state.ratings[record_id][label]
    idx = None if current_selection is None else options.index(current_selection)
    return st.radio(label + ":", options=options, key=f"radio_{label}_{record_id}", horizontal=False, index=idx)


def blank_ratings():
    ratings = [{"Noise": None, "Presence": None, "Multiple": None} for _ in range(3)]
    return ratings


# Data set up

args = get_args()

# Set up session state
if "records" not in st.session_state:
    st.session_state.records, st.session_state.answer_key = generate_item()
    st.session_state.recording_ids = [rec["recording_id"] for rec in st.session_state.records]
    st.session_state.ratings = {rid: ratings[rid] for rid in st.session_state.recording_ids}
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "next_question" not in st.session_state:
    st.session_state.next_question = False
if "selected" not in st.session_state:
    st.session_state.selected = None


# Layout starts here...

st.title("Odd Bird Out")

for i, rec in enumerate(st.session_state.records):
    recording_id = st.session_state.recording_ids[i]
    with st.container():
        button_col, audio_col, image_col = st.columns([.5, 4, 1])

        with button_col:
            if st.session_state.submitted:
                if i == st.session_state.answer_key:
                    st.button("✅", key=f"btn_{i}")
                elif i == st.session_state.selected:
                    st.button("❌", key=f"btn_{i}")
            elif st.button("ABC"[i], key=f"btn_{i}"):
                st.session_state.selected = i
                st.session_state.submitted = True
                st.rerun()

        with audio_col:
            audio_widget(rec)
            credit(rec, st.session_state.submitted)

        with image_col:
            if st.session_state.submitted:
                st.image(BIRD_IMAGE_DIR / (rec["scientific_name"] + ".jpg"), use_container_width=False)
            else:
                st.markdown("<h1 style='text-align: center; color: gray;'>?</h1>", unsafe_allow_html=True)

    if args.rate:
        with st.container():
            _, presence_col, noise_col, multiple_col = st.columns([.5] + [5/3]*3)

            with presence_col:
                st.session_state.ratings[recording_id]["Presence"] = rating_widget(
                    recording_id, label="Presence",  options=["Full", "Sparse", "Delayed"]
                )

            with noise_col:
                st.session_state.ratings[recording_id]["Noise"] = rating_widget(
                    recording_id, label="Noise",  options=["None", "Okay", "Bad"]
                )

            with multiple_col:
                st.session_state.ratings[recording_id]["Multiple"] = rating_widget(
                    recording_id, label="Multiple",  options=["None", "Okay", "Bad"]
                )


# --- Feedback ---
if st.session_state.submitted:
    if st.session_state.selected == st.session_state.answer_key:
        st.success("✅ Correct!")
    else:
        st.error(f"❌ Incorrect.")

# --- Next Question Button ---
if st.session_state.submitted and st.button("Next Question"):
    # Optional handling of ratings
    if args.rate:
        for recording_id, rating_data in st.session_state.ratings.items():
            ratings[recording_id] = rating_data
        with open(RATINGS_LOG_PATH, "w") as f:
            json.dump(ratings, fp=f, indent=4)

    st.session_state.records, st.session_state.answer_key = generate_item()
    st.session_state.recording_ids = [rec["recording_id"] for rec in st.session_state.records]
    st.session_state.ratings = {rid: ratings[rid] for rid in st.session_state.recording_ids}
    st.session_state.submitted = False
    st.session_state.selected = None

    st.rerun()
