from flask import Flask
from authorize import *

app = Flask(__name__)

@app.route("/")
def hello_world():
        return "<p>Hello, World!</p>"

@app.route("/wallet/<chain>")
def wallet(chain):
        connect='http://scully:sw33tp0tat0@btc.metagamer.org:18331'
        blockchain = AuthServiceProxy(connect, timeout=120)
        authorizer = Authorizer(blockchain)
        authorizer.updateWallet()
        return f"wallet for {chain}"

