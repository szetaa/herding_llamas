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

from herder import Herder


app = FastAPI()
herder_instance = None

# herder: Herder


@app.on_event("startup")
async def startup():
    logging.basicConfig(level=logging.INFO)
    global herder_instance
    herder_instance = await Herder.create()
    app.mount("/UI", StaticFiles(directory="UI"), name="UI")
    # background_tasks = BackgroundTasks()
    # background_tasks.add_task(herder.refresh)  # Start the refresh loop


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class User(BaseModel):
    user_key: str
    name: str
    role: str
    limit: list


def authenticate_token(token: str = Depends(oauth2_scheme)):
    for user_key, user_data in herder_instance.users.items():
        if user_data["token"] == token:
            _user = User(
                user_key=user_key,
                name=user_data["name"],
                role=user_data["role"],
                limit=user_data.get("limit", []),
            )
            return _user
    # if no user matches the token, raise an exception
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def authorize_token(
    user,
    prompt_key=None,
    api_path=None,
):
    authorized = herder_instance.authorize(
        user=user, prompt_key=prompt_key, api_path=api_path
    )
    if authorized["authorized"]:
        return user
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=authorized["message"],
            headers={"WWW-Authenticate": "Bearer"},
        )


from functools import wraps


def authorize_endpoint(func):
    # Create decorator for authorization of API entry points.
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extracting request and data from the arguments
        request = kwargs.get("request")
        data = kwargs.get("data", {})

        token = await oauth2_scheme(request)

        # Authenticate
        user = authenticate_token(token)

        request.state.user = user

        # Authorize
        await authorize_token(
            user=user,
            api_path=request.url.path,
            prompt_key=data.get("prompt_key", None),
        )

        # If authorized, continue processing the original function
        return await func(*args, **kwargs)

    return wrapper


@app.get("/api/v1/allowed_tabs")
@authorize_endpoint
async def api_allowed_tabs(request: Request):
    allowed_tabs = herder_instance.roles[request.state.user.user_key]["allow_tabs"]
    return allowed_tabs


# Orchestrator requests
@app.get("/api/v1/llamas")
@authorize_endpoint
async def api_get_llamas(request: Request):
    """
    Get a list of connected large language model instances (llamas).

    This function retrieves the list of connected llamas, which will be
    displayed in an admin form.

    Args:
        None

    Returns:
        list: A list of connected llamas.

    Raises:
        HTTPException: If the user is not authorized to access this endpoint.

    """
    herder_instance.llamas = await herder_instance.load_llamas()
    print(herder_instance.llamas)
    return herder_instance.llamas


@app.get("/api/v1/prompts")
@authorize_endpoint
async def api_get_prompts(request: Request):
    """
    Get a list of configured prompts available on connected llamas.

    This function retrieves the list of prompts that are currently available on
    the connected llamas. This list will be used to populate a dropdown menu in
    the prompt engineering form and can serve as searchable index for API consumers.

    Args:
        None

    Returns:
        dict: A dictionary containing a list of prompts. Each prompt is represented
              as a dictionary with 'prompt' and 'name' keys, to be used in a drop-down.

    Raises:
        HTTPException: If the user is not authorized to access this endpoint.

    """
    _allowed_prompts = herder_instance.roles[request.state.user.user_key][
        "allow_prompts"
    ]
    _prompts = [
        {"prompt": key, "name": key}  # value["name"]}
        for key, value in herder_instance.prompter.prompts.items()
        if key in herder_instance.roles[request.state.user.user_key]["allow_prompts"]
        and key in _allowed_prompts
    ]
    return {"prompts": _prompts}


@app.post("/api/v1/infer")
@authorize_endpoint
async def api_post_infer(request: Request, data: dict):
    """
    Process inference of a user request.

    This function takes a user's input data, embeds it inside the chosen prompt (model-specific system / instruction messages),
    selects relevant instance among the registered llama-nodes (which can handle the prompt type) and sends it through a trusted
    channel to trigger downstream inference. Authorization and logging (incl. node statistics) will be handled centrally
    by the orchestrator.
    The generated inference ID allows to collect feedback to a given request (scoring).

    Args:
        data (dict): The user's input data for inference.

        Format:
        {
            'infer_input':  <raw request>,
            'prompt_key':   <key from prompt store>,
            'param':        <Optional overwrite of generation parameter like temperature or max output tokens>
        }

    Returns:
        dict: A dictionary containing the inference result text and the inference ID.

    Raises:
        HTTPException: If the user is not authorized to access this endpoint.

    """
    data["user_key"] = request.state.user.user_key
    response, inference_id, status_code = await herder_instance.infer(data)

    if status_code == 200:
        response_data = {
            "text": response.json()["response"],
            "inference_id": inference_id,
        }
        return response_data
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response["message"],
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.post("/api/v1/score")
@authorize_endpoint
async def api_score(request: Request, data: dict):
    """
    Provide feedback in the form of scoring (1-5 stars) on a given response.

    This function takes a dictionary containing an inference_id and a score,
    and updates the scoring for the specified inference in the database.

    Args:
        data (dict): A dictionary containing an 'inference_id' which is the id
                     of the inference to be updated and a 'score' which is the
                     new score (1-5 stars) for the inference.

    Returns:
        None

    Raises:
        HTTPException: If the user is not authorized to access this endpoint.

    """
    herder_instance.database.update_inference(data["inference_id"], data)


@app.post("/api/v1/feedback")
@authorize_endpoint
async def api_feedback(request: Request, data: dict):
    """
    Provide written feedback (comments) on a given response.

    This function takes a dictionary containing an inference_id and a feedback
    comment, and updates the feedback for the specified inference in the database.

    Args:
        data (dict): A dictionary containing an 'inference_id' which is the id
                     of the inference to be updated and 'feedback' which is the
                     feedback comment for the inference.

    Returns:
        None

    Raises:
        HTTPException: If the user is not authorized to access this endpoint.

    """
    herder_instance.database.update_inference(data["inference_id"], data)


@app.get("/api/v1/history")
@authorize_endpoint
async def api_get_history(request: Request):
    """
    Fetch the history of recent requests.

    This function retrieves the history of recent requests including raw input,
    prompt, response, input/output tokens, elapsed time, scoring and feedback.

    Args:
        None

    Returns:
        list: A list of dictionaries where each dictionary contains details of an inference
              including raw input, prompt, response, input/output tokens, elapsed time,
              scoring and feedback.

    Raises:
        HTTPException: If the user is not authorized to access this endpoint.

    """
    history = herder_instance.database.list_inference()
    return history


@app.post("/api/v1/switch_model")
@authorize_endpoint
async def api_switch_model(request: Request, data: dict):
    """
    Switch the loaded model on a given node.

    This function takes a dictionary containing a node id and a model id,
    switches the model loaded on the specified node, and carries out garbage
    collection and clearing of GPU memory.

    Args:
        data (dict): A dictionary containing 'node_key' which is the id
                     of the node whose model is to be switched and 'model_key'
                     which is the id of the new model to be loaded.

    Returns:
        dict: A dictionary containing the response of the switching operation.

    Raises:
        HTTPException: If the user is not authorized to access this endpoint.
    """
    response = await herder_instance.switch_model(data)
    return response.json()
