#!/bin/sh

# Python 3.10 required. Then install all required packages:
# pip install -r loaders/load_requirements.txt
# Note to myself: source activate herding_llamas

# Make sure to have set the system variable with your secret between herder and llamas:
# export HERDING_LLAMAS_SECRET=your_secret_123
uvicorn app:app --host 0.0.0.0 --port 8081 --reload
