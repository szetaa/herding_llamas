from fastapi import FastAPI
import pprint
import requests
import os
import time

app = FastAPI()

app.state.TARGET_MODEL = "togethercomputer/llama-2-13b"

BASE_URL = "https://api.together.xyz"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "Authorization": f"Bearer {os.environ.get('TOGETHER_TOKEN')}",
}


@app.get("/api/v1/models")
def api_together_models():
    url = f"{BASE_URL}/instances"
    print(app.state.TARGET_MODEL)

    response = requests.get(url, headers=headers)
    response_json = response.json()

    result = {
        "models": [
            {"option": key, "selected": key == app.state.TARGET_MODEL}
            for (key, value) in response_json.items()
            if value == True
        ],
        "loaded_model": app.state.TARGET_MODEL,
        "system_stats": None,
    }
    return result


@app.post("/api/v1/load_model")
async def api_load_model(data: dict):
    app.state.TARGET_MODEL = data["model_key"]
    print("changed target model to", app.state.TARGET_MODEL)
    return {"loaded": app.state.TARGET_MODEL}


@app.post("/api/v1/infer")
def api_together_infer(data: dict):
    url = f"{BASE_URL}/inference"

    payload = {
        "model": app.state.TARGET_MODEL,
        "prompt": data["infer_input"],
        "max_tokens": 20,
        "stop": ["\n:"],
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

    end_time = time.time()
    elapsed_seconds = end_time - start_time

    data["input_tokens"] = 0
    data["output_tokens"] = 0
    data["elapsed_seconds"] = elapsed_seconds
    data["response"] = response_json["output"]["choices"][0]["text"].strip()
    data["model_name"] = response_json["model"]

    # _response = llama.infer(data=data)
    return data


# togethercomputer/RedPajama-INCITE-7B-Chat
