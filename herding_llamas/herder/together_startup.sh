#!/bin/sh
source activate herding

# Make sure to have set the system variable with your secret between herder and llamas:
# export TOGETHER_TOKEN=your_secret_together_token

uvicorn wrapper_together:app --host localhost --port 8095 --reload
