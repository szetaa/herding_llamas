# Python 3.10 required. Then install all required packages:
# pip install -r loaders/load_requirements.txt

# Note to myself: source activate herding_llamas
uvicorn app:app --host 0.0.0.0 --port 8081 --reload
