from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
import logging
import yaml
import requests
import json

from herder import Herder

app = FastAPI()


async def startup():
    logging.basicConfig(level=logging.INFO)
    global herder
    herder = await Herder.create()
    app.mount("/UI", StaticFiles(directory="UI"), name="UI")


app.add_event_handler("startup", startup)


async def authorize(request: Request):
    pass
    ## Example to check block of not allowed prompts
    ## TOOD: Implement role/license based permission model
    # try:
    #     request_json = await request.json()
    #     target_prompt = request_json["prompt_key"]
    # except Exception as e:
    #     target_prompt = None
    # if target_prompt not in [None, "llama_2_keep_it_short"]:
    #     print("EXCEPT")
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail=f"Not licensed for prompt '{target_prompt}'",
    #     )


# Orchestrator requests
@app.get("/api/v1/llamas", dependencies=[Depends(authorize)])
async def api_get_llamas():
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
    await herder.load_llamas()
    return herder.llamas


@app.get("/api/v1/prompts", dependencies=[Depends(authorize)])
async def api_get_prompts():
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
    _prompts = [
        {"prompt": key, "name": key}  # value["name"]}
        for key, value in herder.prompter.prompts.items()
    ]
    return {"prompts": _prompts}


@app.post("/api/v1/infer", dependencies=[Depends(authorize)])
async def api_post_infer(data: dict):
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
    response, inference_id = await herder.infer(data)
    response_data = {"text": response.json()["response"], "inference_id": inference_id}
    return response_data


@app.post("/api/v1/score", dependencies=[Depends(authorize)])
async def api_score(data: dict):
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
    herder.database.update_inference(data["inference_id"], data)


@app.post("/api/v1/feedback", dependencies=[Depends(authorize)])
async def api_feedback(data: dict):
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
    herder.database.update_inference(data["inference_id"], data)


@app.get("/api/v1/history", dependencies=[Depends(authorize)])
async def api_get_history():
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
    history = herder.database.list_inference()
    return history


@app.post("/api/v1/switch_model", dependencies=[Depends(authorize)])
async def api_switch_model(data: dict):
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
    response = await herder.switch_model(data)
    return response.json()
