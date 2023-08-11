from fastapi import FastAPI
import pprint
import requests
import os
import time

app = FastAPI()


@app.get("/api/v1/models")
def api_together_models():
    result = {
        "models": [
            {"option": "togethercomputer/RedPajama-INCITE-7B-Chat", "selected": True},
        ],
        "loaded_model": "togethercomputer/RedPajama-INCITE-7B-Chat",
        "system_stats": {},
    }
    return result


@app.post("/api/v1/infer")
def api_together_infer(data: dict):
    url = "https://api.together.xyz/inference"

    payload = {
        "model": "togethercomputer/RedPajama-INCITE-7B-Instruct",
        "prompt": data["infer_input"],
        "max_tokens": 128,
        "stop": ["Question:"],
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 50,
        "repetition_penalty": 1,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {os.environ.get('TOGETHER_TOKEN')}",
    }

    start_time = time.time()

    response = requests.post(url, json=payload, headers=headers)
    response_json = response.json()
    pprint.pprint(response_json["output"]["raw_compute_time"])
    end_time = time.time()
    elapsed_seconds = end_time - start_time

    data["input_tokens"] = 0
    data["output_tokens"] = 0
    data["elapsed_seconds"] = elapsed_seconds
    data["response"] = response_json["output"]["choices"][0]["text"].strip()

    # _response = llama.infer(data=data)
    return data


# togethercomputer/RedPajama-INCITE-7B-Chat
