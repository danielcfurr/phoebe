from phoebe import BIRDS, RECORDS, ID_LOOKUP
import streamlit as st
from pathlib import Path, PurePosixPath
import random


def generate_item():
    paired_bird, odd_bird = random.sample(BIRDS, k=2)
    paired_id_list = random.sample(ID_LOOKUP[paired_bird], k=2)
    odd_id_list = random.sample(ID_LOOKUP[odd_bird], k=1)
    shuffled_id_list = random.sample(paired_id_list + odd_id_list, k=3)
    return shuffled_id_list, odd_id_list[0]


def audio_widget(record_id):
    record = RECORDS[record_id]
    audio_file = open("audio/" + record["local_processed"], "rb")
    audio_bytes = audio_file.read()
    st.audio(audio_bytes, format="audio/mp3")


def credit(record_id, reveal=True):
    record = RECORDS[record_id]
    if reveal:
        lic_text, lic_number = PurePosixPath(record["lic"]).parts[-2:]
        st.write(f"""
            **{record['en']}** <br>
            <span style="color:gray;">
            [Recording]({record["url"]}): 
            {record["rec"]} 
            ([CC {lic_text} {lic_number}]({record["lic"]})) <br>
            Photo: First Last (License) <br>
            </span>
        """, unsafe_allow_html=True)
    else:
        st.write("""
            *Secret bird* <br>
            <span style="color:gray;">
            Recording: *???* <br>
            Photo: *???* <br>
            </span>
        """, unsafe_allow_html=True)


# Set up session state and some variables

if "current_question" not in st.session_state:
    st.session_state.current_question = generate_item()
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "next_question" not in st.session_state:
    st.session_state.next_question = False
if "selected" not in st.session_state:
    st.session_state.selected = None

print(st.session_state)

record_ids, correct_id = st.session_state.current_question


# Layout starts here...

st.title("Odd Bird Out")

# Show each record vertically
for i, rid in enumerate(record_ids):
    with st.container():
        button_col, audio_col, image_col = st.columns([.5, 4, 1])

        with button_col:
            if st.session_state.submitted:
                if rid == correct_id:
                    st.button("✅", key=f"btn_{rid}")
                elif rid == st.session_state.selected:
                    st.button("❌", key=f"btn_{rid}")
            elif st.button("ABC"[i], key=f"btn_{rid}"):
                st.session_state.selected = rid
                st.session_state.submitted = True
                st.rerun()

        with audio_col:
            audio_widget(rid)
            credit(rid, st.session_state.submitted)

        with image_col:
            if st.session_state.submitted:
                st.image("temp_bird.jpg", use_container_width=True)
            else:
                pass

# --- Feedback ---
if st.session_state.submitted:
    if st.session_state.selected == correct_id:
        st.success("✅ Correct!")
    else:
        st.error(f"❌ Incorrect.")

# --- Next Question Button ---
if st.session_state.submitted and st.button("Next Question"):
    st.session_state.current_question = generate_item()
    st.session_state.submitted = False
    st.session_state.selected = None
    st.rerun()
