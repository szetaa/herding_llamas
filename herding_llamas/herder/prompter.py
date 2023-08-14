import yaml
import jinja2
import pprint


class Prompter:
    def __init__(self):
        self.load_prompts()

    def load_prompts(self, filename="prompts.yml"):
        with open(filename) as f:
            self.prompts = yaml.safe_load(f)

    def render_prompt(self, prompt_key, prompt_values):
        template = jinja2.Template(self.prompts[prompt_key]["prompt"])

        # For API direct access, the system message is usually not sent.
        # Defaulting all prompt variables if not included.
        for variable in self.prompts[prompt_key].get("variables", []):
            for k, v in variable.items():
                if k not in prompt_values:
                    prompt_values[k] = v
                    print(f'INFO: Setting default prompt value for "{k}".')

        prompt = template.render(prompt_values)
        return prompt

    def prepare_request(self, request):
        request["infer_input"] = self.render_prompt(
            prompt_key=request["prompt_key"], prompt_values=request["raw_inputs"]
        )
        request["param"] = self.prompts[request["prompt_key"]].get("param", None)
        for key, value in request.get("infer_mapping", {}).items():
            request[value] = request[key]
