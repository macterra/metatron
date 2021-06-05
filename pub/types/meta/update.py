from jinja2 import Environment, FileSystemLoader
import json

with open("meta.json") as fin:
    meta = json.load(fin)
    type_json = meta['asset']

with open(type_json) as fin:
    t = json.load(fin)
    print(t)
    asset_json = f"io/{t['asset_name']}"
    asset_page = f"io/{t['page_name']}"
    asset_template = t['template']

env = Environment(loader=FileSystemLoader('.'))
template = env.get_template(asset_template)

with open(asset_json) as fin:
    data = json.load(fin)
    print(data)

index = template.render(asset=data)

with open(asset_page, "w") as fout:
    fout.write(index)
