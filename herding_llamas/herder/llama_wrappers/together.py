from fastapi import FastAPI
import requests
import os
import time
import httpx


class WrapTogether:
    def __init__(self, name: str):
        self.name = name
        self.app = FastAPI()
        self.TARGET_MODEL = "togethercomputer/llama-2-13b"
        self.BASE_URL = "https://api.together.xyz"
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {os.environ.get('TOGETHER_TOKEN')}",
        }

        @self.app.get("/api/v1/models")
        async def api_together_models():
            url = f"{self.BASE_URL}/instances"
            print(self.TARGET_MODEL)

            # response = requests.get(url, headers=self.headers)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url=url, headers=self.headers)

            response_json = response.json()

            result = {
                "models": [
                    {"option": key, "selected": key == self.TARGET_MODEL}
                    for (key, value) in response_json.items()
                    if value == True
                ],
                "loaded_model": self.TARGET_MODEL,
                "system_stats": None,
            }
            return result

        @self.app.post("/api/v1/load_model")
        def api_load_model(data: dict):
            self.TARGET_MODEL = data["model_key"]
            print("changed target model to", self.TARGET_MODEL)
            return {"loaded": self.TARGET_MODEL}

        @self.app.post("/api/v1/infer")
        def api_together_infer(data: dict):
            url = f"{self.BASE_URL}/inference"

            payload = {
                "model": self.TARGET_MODEL,
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

            return data
