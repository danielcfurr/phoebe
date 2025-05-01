# phoebe

Phoebe is a project for learning to identify birds by sound. Currently it features one game
titled "Odd Bird Out".


## Workflow

To prepare audio files:

- Record the scientific names of species to be included in [audio/scientific_names.txt](audio/scientific_names.txt)
- Obtain a Xeno-canto API key and store it in [.env](.env) as `XENOCANTO_API_KEY=xxxx`
- Run [audio/manifest.py](audio/manifest.py) to generate a manifest of the available audio files 
  ([audio/data/manifest.csv](audio/data/manifest.csv)) for the chosen species
- Run [audio/download.py](audio/download.py) to populate [audio/raw](audio/raw) with a selection of audio files
- Run [audio/analyze.py](audio/analyze.py) to generate analysis results for the raw audio files 
  ([audio/data/analysis.csv](audio/data/analysis.csv))
- Run [audio/process.py](audio/process.py) to (1) populate [audio/data/processed](audio/data/processed) with a selection
  of clipped files, (2) generate  app data for the selected files 
  ([audio/data/app_data.json](audio/data/app_data.json)), and (3) document license information 
  ([audio/data/licenses.md](audio/data/licenses.md))

Preparing image files for inclusion is a more manual process. Use 
[notebooks/assemble_images.ipynb](notebooks/assemble_images.ipynb) 
to

  - create image files (placed in [images/data/birds](images/data/birds))
  - create metadata for the images (placed in [images/data/bird_images.jsonl](images/data/bird_images.jsonl))
  - document the image licenses (in [images/data/licenses.md](images/data/licenses.md))


## Odd Bird Out

After following the workflow above, a game of Odd Bird Out may be played.

```bash
streamlit run app.py
```

In addition, the game can include the opportunity to rate the audio files. The ratings are stored in 
[ratings.json](ratings.json).

```bash
streamlit run app.py -- --rate
```


## About

This project relies on audio recordings retrieved from 
[xeno-canto.org](https://xeno-canto.org/)
and photographs from 
[commons.wikimedia.org](https://commons.wikimedia.org/),
all of which are made available under Creative Commons licenses. The individual creators
are credited within the game as well as in
[audio/data/licenses.md](audio/data/licenses.md) and
[images/data/licenses.md](images/data/licenses.md). 
The project itself is licensed under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0).
