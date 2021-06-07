from jinja2 import Environment, FileSystemLoader
import json

with open("type.json") as fin:
    t = json.load(fin)
    print(t)
    type_json = f"io/{t['json']}"
    type_page = f"io/{t['html']}"
    page_template = 'template.html'

env = Environment(loader=FileSystemLoader('.'))
template = env.get_template(page_template)

with open(type_json) as fin:
    data = json.load(fin)
    print(data)

index = template.render(asset=data)

with open(type_page, "w") as fout:
    fout.write(index)
