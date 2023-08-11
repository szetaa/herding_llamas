import yaml
import jinja2


class Prompter:
    def __init__(self):
        self.load_prompts()

    def load_prompts(self, filename="prompts.yml"):
        with open(filename) as f:
            self.prompts = yaml.safe_load(f)

    def render_prompt(self, prompt_key, text):
        template = jinja2.Template(self.prompts[prompt_key]["prompt"])
        _prompt_input = {}
        _prompt_input["text"] = text
        prompt = template.render(_prompt_input)
        return prompt

    def prepare_request(self, request):
        request["TEST"] = "test"
        request["infer_input"] = self.render_prompt(
            prompt_key=request["prompt_key"], text=request["raw_input"]
        )
        request["param"] = self.prompts[request["prompt_key"]].get("param", None)
        for key, value in request.get("infer_mapping", {}).items():
            request[value] = request[key]
        print("REQUEST", request)
