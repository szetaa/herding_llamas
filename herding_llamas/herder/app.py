from fastapi import FastAPI, Depends, HTTPException, status, Response, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from typing import Optional
from functools import wraps

import logging
import yaml
import requests
import json
import pprint
import time

from herder import Herder


app = FastAPI()

from llama_wrappers.together import WrapTogether
from herder_app import HerderApp

wrapper_together_one = WrapTogether(name="together_one")
wrapper_together_two = WrapTogether(name="together_two")

# Mount the FastAPI instances of the services to the main app
app.mount(f"/service_{wrapper_together_one.name}", wrapper_together_one.app)
app.mount(f"/service_{wrapper_together_two.name}", wrapper_together_two.app)

main_herder = HerderApp(name="main_herder")


@app.on_event("startup")
async def startup_event():
    await main_herder.initialize()


app.mount(f"/", main_herder.app)
