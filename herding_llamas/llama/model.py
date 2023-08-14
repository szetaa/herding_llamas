import torch
from transformers import (
    StoppingCriteria,
    StoppingCriteriaList,
)
import json
import time


import gc  # garbage collection when switching models


class StoppingCriteriaSub(StoppingCriteria):
    def __init__(self, stops=[], encounters=1):
        super().__init__()
        self.stops = [stop.to("cuda") for stop in stops]

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor):
        for stop in self.stops:
            if torch.all((stop == input_ids[0][-len(stop) :])).item():
                return True

        return False


class ModelLoaders:
    def load(self, model_key):
        self.model_conf = self.conf["models"][model_key]
        custom_loader = self.model_conf.get("custom_loader", "default")

        # Dynamic loading of custom loaders
        module = __import__(f"loaders.{custom_loader}", fromlist=[custom_loader])
        load_func = getattr(module, custom_loader)
        return load_func(self, model_key)


class LanguageModel(ModelLoaders):
    def __init__(self):
        self.loaded_model = self.conf["startup_model"]
        self.load_model(self.loaded_model)

    def load_model(self, model_key):
        print("garbage collection..")
        if hasattr(self, "model"):
            del self.model
        gc.collect()
        torch.cuda.empty_cache()
        # init
        self.loaded_model = model_key
        loaded = self.load(model_key)
        return loaded

    def infer(self, data: dict):
        start_time = time.time()

        infer_input = data.get("infer_input", "NOTHING")
        param = data.get("param", {})
        _stop_words_ids = [
            self.tokenizer(
                stop_word,
                add_special_tokens=False,
                return_tensors="pt",
            )
            .input_ids.cuda()
            .squeeze()
            for stop_word in param.get("stop_words", [])
        ]
        # Workaround to cut out <s>
        _stop_words_ids = _stop_words_ids + [x[1:] for x in _stop_words_ids]

        ## uncomment here to debug non-stopping prompts
        # print('STOP WORDS IDS:',_stop_words_ids)
        # for x in _stop_words_ids:
        #     print(f'STOP WORD: "{x}" -->"{self.tokenizer.decode(x)}"<--')

        _stopping_criteria = StoppingCriteriaList(
            [StoppingCriteriaSub(stops=_stop_words_ids)]
        )

        input_ids = self.tokenizer(infer_input, return_tensors="pt").input_ids.cuda()
        num_input_tokens = input_ids.shape[1]
        output = self.model.generate(
            inputs=input_ids,
            stopping_criteria=_stopping_criteria,
            temperature=param.get("temperature", 0.7),
            max_new_tokens=param.get("max_new_tokens", 100),
            early_stopping=param.get("early_stopping", False),
            do_sample=param.get("do_sample", False),
            top_p=param.get("top_p", 1.0),
            typical_p=param.get("typical_p", 1.0),
            repetition_penalty=param.get("repetition_penalty", 1.0),
            top_k=param.get("top_k", 50),
            min_length=param.get("min_length", 0),
            no_repeat_ngram_size=param.get("no_repeat_ngram_size", 0),
            num_beams=param.get("num_beams", 1),
            penalty_alpha=param.get("penalty_alpha", 0),
            length_penalty=param.get("length_penalty", 1.0),
        )
        num_output_tokens = output.shape[1]
        output_str = self.tokenizer.decode(output[0])
        output_str = (
            output_str.replace(infer_input, "")
            .replace("<s>", "")
            .replace("</s>", "")
            .strip()
        )
        end_time = time.time()
        elapsed_seconds = end_time - start_time

        return {
            "response": output_str,
            "input_tokens": num_input_tokens,
            "output_tokens": num_output_tokens,
            "elapsed_seconds": elapsed_seconds,
            "model_name": self.loaded_model,
        }
