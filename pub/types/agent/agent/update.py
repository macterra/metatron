from jinja2 import Environment, FileSystemLoader
import json

with open("type.json") as fin:
    t = json.load(fin)
    print(t)
    asset_json = f"io/{t['asset_name']}"

    if 'page_name' in t:
        asset_page = f"io/{t['page_name']}"
    else:
        asset_page = 'index.html'

    if 'template' in t:
        asset_template = t['template']
    else:
        asset_template = 'template.html'

env = Environment(loader=FileSystemLoader('.'))
template = env.get_template(asset_template)

with open(asset_json) as fin:
    data = json.load(fin)
    print(data)

index = template.render(asset=data)

with open(asset_page, "w") as fout:
    fout.write(index)
