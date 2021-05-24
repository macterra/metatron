from flask import Flask, render_template
from authorize import *

app = Flask(__name__)

@app.route("/")
def index():
        user = {'username': 'Miguel'}
        return render_template('index.html', title='Home', user=user)

@app.route("/wallet/<chain>")
def wallet(chain):
        connect=os.environ.get(f"{chain}_CONNECT")
        blockchain = AuthServiceProxy(connect, timeout=120)
        authorizer = Authorizer(blockchain)
        authorizer.updateWallet()
        return render_template('wallet.html', chain=chain, authorizer=authorizer)

@app.route("/meta/<cid>")
def meta(cid):
        meta = getMeta(cid)
        return render_template('meta.html', cid=cid, meta=meta)

