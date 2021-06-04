from jinja2 import Environment, FileSystemLoader
import json

meta_json = f"../meta.json"
meta_template = "template-meta.html"
meta_index = "../meta.html"

env = Environment(loader=FileSystemLoader('.'))
template = env.get_template(meta_template)

with open(meta_json) as fin:
    data = json.load(fin)
    print(data)

index = template.render(meta=data)

with open(meta_index, "w") as fout:
    fout.write(index)
