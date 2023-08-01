from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from starlette.requests import Request

import logging
import yaml
import pprint

from model import LanguageModel
from sys_stats import SystemStats


class Llama(LanguageModel):
    def __init__(self):
        self.load_conf()
        self.system_stats = SystemStats()
        LanguageModel.__init__(self)

    def load_conf(self):
        with open("conf.yml") as f:
            self.conf = yaml.safe_load(f)


llama = Llama()

logging.basicConfig(level=logging.INFO)

app = FastAPI()
# router = APIRouter()

API_KEY_NAME = llama.conf["API_KEY_NAME"]
API_KEY = llama.conf["API_KEY"]


def get_api_key(request: Request):
    _api_key = request.headers.get(API_KEY_NAME)
    if _api_key == API_KEY:
        return _api_key
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key"
        )


@app.get("/api/v1/models")
async def api_get_models(api_key: str = Depends(get_api_key)):
    _models = [
        {"option": key, "selected": key == llama.loaded_model}
        for key, value in llama.conf["models"].items()
    ]
    _system_stats = llama.system_stats.collect_system_stats()
    return {
        "models": _models,
        "loaded_model": llama.loaded_model,
        "system_stats": _system_stats,
    }


@app.post("/api/v1/load_model")
async def api_load_model(data: dict, api_key: str = Depends(get_api_key)):
    print("DATA:", data)
    _result = llama.load_model(data["model_key"])
    return _result


@app.post("/api/v1/infer")
async def api_infer(data: dict, api_key: str = Depends(get_api_key)):
    pprint.pprint(data, width=120)
    _response = llama.infer(data=data)
    return _response


@app.get("/api/v1/system_stats")
async def api_system_stats(api_key: str = Depends(get_api_key)):
    _response = llama.system_stats.collect_system_stats()
    pprint.pprint(_response)
    return _response
