#!/bin/sh
source activate herding

# Make sure to have set the system variable with your secret between herder and llamas:
# export HERDING_LLAMAS_SECRET=your_secret_123

uvicorn app:app --host 0.0.0.0 --port 8090 --reload
