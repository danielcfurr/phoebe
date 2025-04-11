from phoebe import BIRDS, RECORDS, ID_LOOKUP
import streamlit as st
from pathlib import Path
import random

def audio_widget(record_id, show_credit):
    record = RECORDS[record_id]
    audio_file = open("audio/" + record["local_processed"], "rb")
    audio_bytes = audio_file.read()
    st.audio(audio_bytes, format="audio/mp3")
    if show_credit:
        st.text(f"Recording by {record["rec"]} ({record["lic"]})")
    else:
        st.text(f"Recording by ??? (???)")


def generate_item():
    paired_bird, odd_bird = random.sample(BIRDS, k=2)
    paired_id_list = random.sample(ID_LOOKUP[paired_bird], k=2)
    odd_id_list = random.sample(ID_LOOKUP[odd_bird], k=1)
    shuffled_id_list = random.sample(paired_id_list + odd_id_list, k=3)
    return shuffled_id_list, odd_id_list[0]


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

# Audio widgets
for rid in record_ids:
    audio_widget(rid, st.session_state.submitted)

# --- Choices (disable after submit) ---
selected = st.radio(
    "Who is the odd bird?",
    record_ids,
    index=record_ids.index(st.session_state.selected) if st.session_state.selected else 0,
    disabled=st.session_state.submitted
)
st.session_state.selected = selected

# --- Submit Button (disable after submit) ---
submit_button = st.button("Submit", disabled=st.session_state.submitted)

# Handle submission
if submit_button and not st.session_state.submitted:
    st.session_state.submitted = True
    st.rerun()  # So the radio and submit button updates immediately as disabled

# --- Feedback ---
if st.session_state.submitted:
    if st.session_state.selected == correct_id:
        st.success("✅ Correct!")
    else:
        st.error(f"❌ Incorrect. The correct answer was **{correct_id}**.")

# --- Next Question Button ---
if st.session_state.submitted and st.button("Next Question"):
    st.session_state.current_question = generate_item()
    st.session_state.submitted = False
    st.session_state.selected = None
    st.rerun()
