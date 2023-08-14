import yaml
import pprint
import requests
import httpx
import json
import os
from urllib.parse import urlparse
import asyncio

from prompter import Prompter
from database import Database
from llm_queue import TaskQueue, Worker


class Herder:
    def __init__(self):  # , prompter, database, task_queue):
        self.load_users()
        self.load_roles()
        self.prompter = Prompter()
        self.database = Database(db_url="sqlite:///herder.sqlite")
        self.workers = {}
        self.task_queue = TaskQueue()

    def load_users(self):
        with open("users.yml", "r") as f:
            self.users = yaml.safe_load(f)

    def load_roles(self):
        with open("roles.yml", "r") as f:
            self.roles = yaml.safe_load(f)

    async def refresh(self):
        while True:
            await asyncio.sleep(3600)
            self.load_users()
            self.load_roles()

    def authorize(self, user, prompt_key=None, api_path=None):
        # check API path allowed
        if api_path not in self.roles[user.role]["allow_api_paths"]:
            return {
                "authorized": False,
                "message": f"Unauthorized request: {api_path} for user role: {user.role}",
            }
        # check prompt allowed?
        if (
            prompt_key is not None
            and prompt_key not in self.roles[user.role]["allow_prompts"]
        ):
            return {
                "authorized": False,
                "message": f"Unauthorized prompt: {prompt_key} for user role: {user.role}",
            }
        # check node allowed? - not necessary here, filter on allowed nodes in _candidates.

        # check if any user limits reached
        for limit in user.limit:
            actual = self.database.get_user_statistics(user.user_key, limit["interval"])
            if actual[limit["type"]] >= limit["limit"]:
                return {
                    "authorized": False,
                    "message": f"Limit reached: {limit['type']} ({actual[limit['type']]}>={limit['limit']}) in last {limit['interval']}h for user: {user.user_key}",
                }

        # Finally
        return {"authorized": True}

    async def load_llamas(self, load_stats=True):
        with open("llamas.yml") as f:
            self.conf = yaml.safe_load(f)
        self.llamas = self.conf
        if load_stats:
            _llama_stats = self.database.get_node_statistics()
            for _llama in self.llamas.copy():
                print("loading llama", _llama)
                try:
                    _url = f"{self.conf[_llama]['base_url']}/api/v1/models"
                    _headers = self.get_header(self.conf[_llama])
                    async with httpx.AsyncClient() as client:
                        _models = await client.get(_url, headers=_headers)
                    _models_json = _models.json()
                    self.llamas[_llama]["models"] = _models_json["models"]
                    self.llamas[_llama]["loaded_model"] = _models_json["loaded_model"]
                    self.llamas[_llama]["system_stats"] = _models_json.get(
                        "system_stats", {}
                    )
                    self.llamas[_llama]["infer_stats"] = _llama_stats.get(_llama, {})
                    self.llamas[_llama]["worker_started"] = _llama in self.workers
                    self.llamas[_llama]["mapped_prompts"] = [
                        key
                        for key, value in self.prompter.prompts.items()
                        if self.llamas[_llama]["loaded_model"] in value["target_models"]
                    ]
                except Exception as e:
                    print(f"WARNING: Could not fetch '{_llama}': {e}")
                    self.llamas[_llama]["models"] = [{"option": "offline?"}]
                    self.llamas[_llama]["loaded_model"] = "offline?"
                    self.llamas[_llama]["system_stats"] = {}
                    self.llamas[_llama]["infer_stats"] = {}
                    self.llamas[_llama]["mapped_prompts"] = []
        return self.llamas

    async def start_worker(self, worker_id, skills):
        print("workers before:", [w for w in self.workers])
        print(f"INFO: Starting worker '{worker_id}' listening to prompts: {skills}")
        if worker_id in self.workers:
            await self.stop_worker(worker_id)
        task = asyncio.create_task(
            Worker(
                worker_id=worker_id, task_queue=self.task_queue, skills=skills
            ).start()
        )
        self.workers[worker_id] = task
        print("workers after:", [w for w in self.workers])

    async def stop_worker(self, worker_id):
        task = self.workers.get(worker_id)
        if task:
            task.cancel()
            del self.workers[worker_id]

    async def start_workers(self):
        _workers_created = []
        _workers_skipped = []
        for _llama, value in self.llamas.items():
            if len(value.get("mapped_prompts", [])) > 0:
                _skills = value["mapped_prompts"]
                # print("==> starting worker with skills:", _skills)
                await self.start_worker(_llama, _skills)
                _workers_created.append(_llama)
            else:
                _workers_skipped.append(_llama)
        # print("WORKERS", self.workers)

        print(f"INFO: {len(_workers_created)} queue worker created: {_workers_created}")
        print(f"INFO: {len(_workers_skipped)} queue worker skipped: {_workers_skipped}")

    async def switch_model(self, data: dict):
        _url = f"{self.conf[data['node_key']]['base_url']}/api/v1/load_model"
        _headers = self.get_header(self.conf[data["node_key"]])
        async with httpx.AsyncClient(timeout=30.0) as client:
            _response = await client.post(url=_url, headers=_headers, json=data)
        await self.load_llamas()
        if data["node_key"] in self.workers:
            print("stopping worker:", data["node_key"])
            # print(self.workers)
            await self.stop_worker(data["node_key"])
        await self.start_worker(
            data["node_key"], self.llamas[data["node_key"]]["mapped_prompts"]
        )
        # print("POST SWITCH WORKERS:", self.workers)
        # print("POST SWITCH PROMPTS:", self.llamas[data["node_key"]]["mapped_prompts"])
        return _response

    async def infer(self, data: dict):
        self.prompter.prepare_request(data)

        # node candidates from roles
        _allowed_nodes = self.roles[self.users[data["user_key"]]["role"]]["allow_nodes"]
        print("allowed nodes raw", _allowed_nodes)

        # node candidates from prompt settings

        # Wrapper for queue
        # node_key is injected through lambda function from picking up worker!
        # worker_id == node_key
        async def send_request(data, node_key):
            _node_conf = self.llamas[node_key]
            url = f'{_node_conf["base_url"]}{_node_conf.get("infer_path","/api/v1/infer")}'
            headers = self.get_header(self.llamas[node_key])
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url=url, headers=headers, json=data)
            return node_key, response

        # Adding request to queue
        task_id = await self.task_queue.enqueue_task(
            lambda node_key: send_request(data, node_key),
            data["prompt_key"],
            _allowed_nodes,
        )

        # wait for queue complete event and pick up results
        try:
            await asyncio.wait_for(
                self.task_queue.result_events[task_id].wait(), timeout=30  # 60 * 5
            )
            node_key, response = self.task_queue.results.pop(task_id)
            status_code = 200
        except asyncio.TimeoutError:
            response = {"message": "TIMEOUT: No allowed Llama available!"}
            status_code = 503
            db_inference_id = None
            return response, db_inference_id, status_code

        mask_history = self.users[data["user_key"]].get(
            "opt_out_history_content", False
        )
        response_json = response.json()
        db_inference_record = {
            "user_key": data.get("user_key", "unknown"),
            "node_key": node_key,
            "model_name": response_json.get("model_name"),
            "prompt_key": data.get("prompt_key", "unknown"),
            "prompt_version": "TBD",
            "input_tokens": response_json.get("input_tokens", 0),
            "output_tokens": response_json.get("output_tokens", 0),
            "elapsed_seconds": response_json.get("elapsed_seconds", 0),
            "raw_input": json.dumps(data["raw_inputs"])
            if not mask_history
            else "masked",
            "infer_input": data["infer_input"] if not mask_history else "masked",
            "response": response.json()["response"] if not mask_history else "masked",
        }
        db_inference_id = self.database.create_inference(db_inference_record)

        return response, db_inference_id, status_code

    def get_header(self, llama: dict):
        API_KEY_NAME = llama["API_KEY_NAME"]
        API_KEY = os.environ.get(API_KEY_NAME)
        return {API_KEY_NAME: API_KEY}
