import yaml
import pprint
import requests
import httpx
import json

from prompter import Prompter
from database import Database


class Herder:
    def __init__(self, prompter, database):
        self.prompter = prompter
        self.database = database

    # async classmethod to serve as an alternative constructor.
    @classmethod
    async def create(cls):
        prompter = Prompter()
        database = Database(db_url="sqlite:///herder.sqlite")
        herder = cls(prompter, database)
        await herder.load_llamas()
        return herder

    async def load_llamas(self):
        with open("llamas.yml") as f:
            self.conf = yaml.safe_load(f)
        self.llamas = self.conf
        _llama_stats = self.database.get_node_statistics()
        pprint.pprint(_llama_stats)
        for _llama in self.llamas.copy():
            try:
                _url = f"{self.conf[_llama]['base_url']}/api/v1/models"
                _headers = self.get_header(_llama)
                async with httpx.AsyncClient() as client:
                    _models = await client.get(_url, headers=_headers)
                # _models = requests.get(_url, headers=_headers)
                self.llamas[_llama]["models"] = _models.json()["models"]
                self.llamas[_llama]["loaded_model"] = _models.json()["loaded_model"]
                self.llamas[_llama]["system_stats"] = _models.json().get(
                    "system_stats", {}
                )
                print("ASDFFFFFF")
                pprint.pprint(_llama_stats.get(_llama, {}))
                self.llamas[_llama]["infer_stats"] = _llama_stats.get(_llama, {})
            except Exception as e:
                print(f"Error: Could not fetch '{_llama}': {e}")
                self.llamas[_llama]["models"] = [{"option": "offline?"}]
                self.llamas[_llama]["loaded_model"] = "offline?"
                self.llamas[_llama]["system_stats"] = {}
        # pprint.pprint(self.llamas)

    async def switch_model(self, data: dict):
        _url = f"{self.conf[data['node_key']]['base_url']}/api/v1/load_model"
        _headers = self.get_header(data["node_key"])
        async with httpx.AsyncClient(timeout=30.0) as client:
            _response = await client.post(
                url=_url, headers=_headers, data=json.dumps(data)
            )
        # _response = requests.post(url=_url, headers=_headers, data=json.dumps(data))
        return _response

    # def collect_system_stats(self, data: dict):
    #     _url = f"{self.conf[data['node_key']]['base_url']}/api/v1/system_stats"
    #     _headers = self.get_header(data["node_key"])
    #     _response = requests.get(url=_url, headers=_headers)
    #     return _response

    async def infer(self, data: dict):
        if data.get("prompt_key") is not None:
            data["infer_input"] = self.prompter.render_prompt(
                prompt_key=data["prompt_key"], text=data["raw_input"]
            )
            data["param"] = self.prompter.prompts[data["prompt_key"]].get("param", None)
        else:
            data["infer_input"] = data["raw_input"]
        _candidates = [
            {"node_key": key, "base_url": value["base_url"]}
            for key, value in self.llamas.items()
            if value["loaded_model"]
            in self.prompter.prompts[data["prompt_key"]]["target_models"]
        ]
        if len(_candidates) > 0:
            _node_key = _candidates[0]["node_key"]
            print(f'sending to {_candidates[0]["base_url"]}')
            _url = f'{_candidates[0]["base_url"]}/api/v1/infer'
            _headers = self.get_header(_node_key)
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    url=_url, headers=_headers, data=json.dumps(data)
                )
            pprint.pprint(response)

            # response = requests.post(url=_url, headers=_headers, data=json.dumps(data))
        else:
            response = json.dumps({"response": "EXCEPTION: Backend not available!"})
        print("RES", response.json())
        db_inference_record = {
            "node_key": _node_key,
            "prompt_key": data.get("prompt_key", "unknown"),
            "prompt_version": "TBD",
            "input_tokens": response.json()["input_tokens"],
            "output_tokens": response.json()["output_tokens"],
            "elapsed_seconds": response.json()["elapsed_seconds"],
            "raw_input": data["raw_input"],
            "infer_input": data["infer_input"],
            "response": response.json()["response"],
        }
        db_inference_id = self.database.create_inference(db_inference_record)

        return response, db_inference_id

    def get_header(self, llama: str):
        return {self.conf[llama]["API_KEY_NAME"]: self.conf[llama]["API_KEY"]}
