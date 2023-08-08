from transformers import AutoModelForCausalLM, AutoTokenizer


def load_default(llama, model_key):
    llama.tokenizer = AutoTokenizer.from_pretrained(llama.model_conf["path"])
    llama.model = AutoModelForCausalLM.from_pretrained(llama.model_conf["path"])
    return {"loaded": model_key}
