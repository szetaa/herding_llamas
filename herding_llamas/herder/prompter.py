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
