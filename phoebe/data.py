import json
import random
from pathlib import Path

#print(Path() / "audio" / "data")

with open('audio/data/manifest.json') as f:
    RECORDS = json.load(f)

ID_LOOKUP = {}
for record_id, record in RECORDS.items():
    if record['en'] in ID_LOOKUP.keys():
        ID_LOOKUP[record['en']].append(record_id)
    else:
        ID_LOOKUP[record['en']] = [record_id]

BIRDS = list(ID_LOOKUP.keys())

def generate_record_ids_for_item():
    paired_bird, odd_bird = random.sample(BIRDS, k=2)
    paired_id_list = random.sample(ID_LOOKUP[paired_bird], k=2)
    odd_id_list = random.sample(ID_LOOKUP[odd_bird], k=1)
    shuffled_id_list = random.choice(paired_id_list + odd_id_list)
    return shuffled_id_list, odd_id_list[0]
