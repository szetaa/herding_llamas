from transformers import AutoTokenizer, AutoModelForCausalLM


def load_4bit(llama, model_key):
    llama.tokenizer = AutoTokenizer.from_pretrained(llama.model_conf["path"])
    llama.model = AutoModelForCausalLM.from_pretrained(
        llama.model_conf["path"],
        trust_remote_code=llama.model_conf.get("trust_remote_code", False),
        load_in_4bit=True,
        device_map="auto",
    )
    return {"loaded": model_key}
