from jinja2 import Environment, FileSystemLoader
import sys, json

def generateIndex(asset):
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template("agent.html")

    with open(asset) as fin:
        data = json.load(fin)

    index = template.render(agent=data)

    with open('index.html', "w") as fout:
        fout.write(index)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        asset = sys.argv[1]
        generateIndex(asset)
    else:
        print(f"usage: python { sys.argv[0] } asset")
