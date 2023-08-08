from auto_gptq import AutoGPTQForCausalLM
from transformers import AutoTokenizer


def load_gptq(llama, model_key, use_triton=False):
    llama.tokenizer = AutoTokenizer.from_pretrained(llama.model_conf["path"])
    llama.model = AutoGPTQForCausalLM.from_quantized(
        llama.model_conf["path"],
        model_basename=llama.model_conf.get("basename", None),
        use_safetensors=True,
        trust_remote_code=False,
        device="cuda:0",
        use_triton=use_triton,
        quantize_config=None,
    )
    return {"loaded": model_key}
