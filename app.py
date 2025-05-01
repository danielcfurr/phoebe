import json
import streamlit as st
from pathlib import Path, PurePosixPath
import random
import argparse

NUMBER_QUESTIONS = 10

AUDIO_DIR = Path().resolve() / "audio" / "data" / "processed"
APP_DATA_PATH = Path().resolve() / "audio" / "data" / "app_data.json"
RATINGS_PATH = Path().resolve() / "ratings.json"
BIRD_IMAGE_DATA_PATH = Path().resolve() / "images" / "data" / "bird_images.jsonl"
BIRD_IMAGE_DIR = Path().resolve() / "images" / "data" / "birds"


@st.cache_resource
def load_app_data():
    with open(APP_DATA_PATH) as file:
        recordings = json.load(file)
    scientific_names = list(recordings.keys())
    with open(BIRD_IMAGE_DATA_PATH, "r") as file:
        images = [json.loads(line) for line in file]
        images = {img["scientific_name"]: img for img in images}
    return scientific_names, recordings, images


SCIENTIFIC_NAMES, RECORDINGS, IMAGES = load_app_data()


def main(rate: bool):
    page = st.session_state.get("page", "start")
    st.session_state.counter = st.session_state.get("counter", 1)
    st.session_state.correctness = st.session_state.get("correctness", [])

    if rate:
        st.session_state.rate = True
        st.session_state.ratings = st.session_state.get("ratings", load_ratings())
    else:
        st.session_state.rate = False
        st.session_state.ratings = {}

    if page == "start":
        show_start_page()
    elif st.session_state.counter > NUMBER_QUESTIONS:
        show_conclusion_page()
    elif page == "question":
        show_question_page()
    elif page == "review":
        show_review_page()


def show_start_page():
    st.markdown("""
    ## Odd Bird Out
    
    ### How to play
    
    Listen to three recordings of bird sounds. Two recordings will be of the 
    same species, while one will be of the "odd bird"&mdash;a different species. Your goal is
    to identify which recording is from the odd bird. Repeat this challenge ten times 
    to see how high you can score.
    
    ### About
    
    This software relies on audio recordings retrieved from 
    [xeno-canto.org](https://xeno-canto.org/)
    and photographs from 
    [commons.wikimedia.org](https://commons.wikimedia.org/),
    all of which are made available under Creative Commons licenses. The individual creators
    are credited within the game. This software is a part of 
    [Phoebe](https://github.com/danielcfurr/phoebe), 
    a project by 
    [Daniel C. Furr](https://github.com/danielcfurr), 
    and is licensed under 
    [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0).
    """)

    if st.button("Start game", key=f"btn_start"):
        st.session_state.page = "question"
        generate_question()
        st.rerun()


def show_question_page():
    st.markdown("## Odd Bird Out")
    progress_widget()
    st.markdown("### Which is the odd bird?")

    opt_1 = render_option(0, st.session_state.recordings[0], active=True)
    if st.session_state.rate:
        render_ratings(st.session_state.recordings[0])

    opt_2 = render_option(1, st.session_state.recordings[1], active=True)
    if st.session_state.rate:
        render_ratings(st.session_state.recordings[1])

    opt_3 = render_option(2, st.session_state.recordings[2], active=True)
    if st.session_state.rate:
        render_ratings(st.session_state.recordings[2])

    x = [opt_1, opt_2, opt_3]

    if any(x):
        st.session_state.answer = x.index(True)
        st.session_state.page = "review"
        st.rerun()



def show_review_page():
    st.markdown(f"## Odd Bird Out")
    progress_widget()

    correct = st.session_state.answer == st.session_state.key

    if correct:
        st.markdown(f"""### Result: <span style="color:green">Correct!</span>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""### Result: <span style="color:orange">Incorrect</span>""", unsafe_allow_html=True)

    _ = render_option(0, st.session_state.recordings[0], active=False)
    if st.session_state.rate:
        render_ratings(st.session_state.recordings[0])

    _ = render_option(1, st.session_state.recordings[1], active=False)
    if st.session_state.rate:
        render_ratings(st.session_state.recordings[1])

    _ = render_option(2, st.session_state.recordings[2], active=False)
    if st.session_state.rate:
        render_ratings(st.session_state.recordings[2])

    if st.button("Next", key=f"btn_next"):
        if st.session_state.rate:
            save_ratings()
        st.session_state.page = "question"
        st.session_state.counter += 1
        st.session_state.correctness.append(correct)
        generate_question()
        st.rerun()


def show_conclusion_page():
    st.markdown("## Odd Bird Out")
    progress_widget()

    score = int(sum(st.session_state.correctness) / NUMBER_QUESTIONS * 100)
    st.markdown(f"""
    ### Your score for the round is {score}%
    
    Thank you for playing and please try again!
    """)

    if st.button("Restart", key=f"btn_restart"):
        st.session_state.clear()
        st.rerun()


def load_ratings():
    if RATINGS_PATH.exists():
        with open(RATINGS_PATH, "r") as file:
            ratings = json.load(file)
    else:
        ratings = {}
        for bird, records in RECORDINGS.items():
            for record in records:
                ratings[record["recording_id"]] = {
                    "start_sec": record["start_sec"],
                    "end_sec": record["end_sec"],
                    "Noise": None,
                    "Presence": None,
                    "Multiple": None,
                }
    return ratings


def save_ratings():
    with open(RATINGS_PATH, "w") as file:
        json.dump(st.session_state.ratings, fp=file, indent=4)


def audio_widget(recording):
    file_path = AUDIO_DIR / recording["file_name"]
    audio_file = open(file_path, "rb")
    audio_bytes = audio_file.read()
    st.audio(audio_bytes, format="audio/mp3")


def generate_question():
    odd_bird, paired_bird = random.sample(SCIENTIFIC_NAMES, k=2)
    odd_list = random.sample(RECORDINGS[odd_bird], k=1)
    paired_list = random.sample(RECORDINGS[paired_bird], k=2)
    complete_list = odd_list + paired_list
    order = random.sample(range(3), k=3)

    st.session_state.key = order.index(0)
    st.session_state.recordings = [complete_list[j] for j in order]
    st.session_state.images = [IMAGES[rec["scientific_name"]] for rec in st.session_state.recordings]


def render_option(i, recording, active=True):
    with st.container():
        button_col, recording_col, image_col = st.columns([.5, 4, 1])

        with button_col:
            if active:
                selected = st.button("ABC"[i], key=f"btn_{i}", )
            elif st.session_state.key == i:
                st.button("✅", key=f"btn_{i}", disabled=True)
                selected = None
            elif st.session_state.answer == i:
                st.button("❌", key=f"btn_{i}", disabled=True)
                selected = None
            else:
                selected = None

        with recording_col:
            audio_widget(recording)
            if active:
                st.write("""
                    *Secret bird* <br>
                    <span style="color:gray;">
                    Audio: *???* <br>
                    Photo: *???* <br>
                    </span>
                """, unsafe_allow_html=True)
            else:
                recording_lic_text, recording_lic_number = PurePosixPath(recording["license"]).parts[-2:]
                scientific_name = recording["scientific_name"]
                image = IMAGES[scientific_name]
                image_lic_text, image_lic_number = PurePosixPath(image["license_url"]).parts[-3:-1]
                st.write(f"""
                    **{recording["common_name"]}**
                    (*{scientific_name}*) <br>
                    <span style="color:gray;">
                    [Audio]({recording["url"]}): 
                    {recording["author"]} 
                    ([CC {recording_lic_text} {recording_lic_number}]({recording["license"]})).
                    Cropped from original. <br>
                    [Photo]({image["url"]}): 
                    {image["author"]} 
                    ([CC {image_lic_text} {image_lic_number}]({image["license_url"]})).
                    Cropped from original.
                    </span>
                """, unsafe_allow_html=True)

        with image_col:
            if active:
                st.markdown("<h1 style='text-align: center; color: gray;'>?</h1>", unsafe_allow_html=True)
            else:
                st.image(BIRD_IMAGE_DIR / (recording["scientific_name"] + ".jpg"), use_container_width=False)

    return selected


def rating_widget(record_id, label, options):
    current_selection = st.session_state.ratings[record_id][label]
    idx = None if current_selection is None else options.index(current_selection)
    return st.radio(label + ":", options=options, key=f"radio_{label}_{record_id}", horizontal=False, index=idx)


def render_ratings(recording):
    recording_id = recording["recording_id"]
    with st.container():
        _, presence_col, noise_col, multiple_col = st.columns([.5] + [5 / 3] * 3)

        with presence_col:
            st.session_state.ratings[recording_id]["Presence"] = rating_widget(
                recording_id, label="Presence", options=["Full", "Sparse", "Delayed"]
            )

        with noise_col:
            st.session_state.ratings[recording_id]["Noise"] = rating_widget(
                recording_id, label="Noise", options=["None", "Okay", "Bad"]
            )

        with multiple_col:
            st.session_state.ratings[recording_id]["Multiple"] = rating_widget(
                recording_id, label="Multiple", options=["None", "Okay", "Bad"]
            )


def progress_widget():
    correctness = st.session_state.correctness
    number_answered = len(correctness)
    spaces = "&nbsp;" * 5

    text = "<div style='font-size: 24px;'>"
    for i in range(NUMBER_QUESTIONS):
        if i == number_answered:
            text += f"<span style='font-weight: bold;'>{i + 1}</span>{spaces}"
        elif i < number_answered:
            if correctness[i]:
                text += f"<span style='color: green;'>{i + 1}</span>{spaces}"
            else:
                text += f"<span style='color: orange;'>{i + 1}</span>{spaces}"
        else:
            text += f"<span style='color: gray;'>{i + 1}</span>{spaces}"

    text += "</div>"

    st.markdown(text, unsafe_allow_html=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rate",
        action="store_true",
        help="Enable rating mode"
    )

    args, _ = parser.parse_known_args()

    main(args.rate)
