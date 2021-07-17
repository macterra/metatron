import os
import redis
import xidb
from version import version

from flask import Flask, render_template, redirect, request, flash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from authorize import Authorizer
from scanner import ScannerDb
from urllib.parse import urlparse

class TransferForm(FlaskForm):
    cid = StringField('cid')
    addr = StringField('address')
    authorize = SubmitField('authorize')
    transfer = SubmitField('transfer')
    confirm = SubmitField('confirm')
    cancel = SubmitField('cancel')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

bootstrap = Bootstrap(app)

#print(app.config)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/about")
def about():
    return render_template('about.html', version=version)

@app.route("/explorer")
def explorer():
    db = ScannerDb()
    return render_template('explorer.html', assets=db.getAssets())

@app.route("/scanner")
def scanner():
    db = ScannerDb()
    return render_template('scanner.html', status=db.getStatus())

@app.route("/reset")
def resetDb():
    db = ScannerDb()
    db.flushall()
    return redirect("/scanner")

@app.route("/vault/<chain>")
def vault(chain):    
    authorizer = Authorizer(chain)
    authorizer.updateWallet()
    return render_template('vault.html', authorizer=authorizer)

@app.route("/receive/<chain>")
def receive(chain):    
    authorizer = Authorizer(chain)
    addr = authorizer.getAddress()
    flash(f"receive address: {addr}")
    return redirect(f"/vault/{chain}")

@app.route("/pin/chain/<chain>")
def pinAssets(chain):    
    authorizer = Authorizer(chain)
    authorizer.updateWallet()
    for asset in authorizer.assets:
        if xidb.pin(asset.cid):
            flash(f"pinned {asset.cid}")
    return redirect(f"/vault/{chain}")

@app.route("/ipfs/<path:path>")
def ipfs(path):
    o = urlparse(request.base_url)
    return redirect(f"http://{o.hostname}:8080/ipfs/{path}", 302)

@app.route("/chain/<chain>")
def chainExplorer(chain):
    if chain == 'TSR':
        return redirect("https://openchains.info/coin/tesseract/", 302)
    if chain == 'tBTC':
        return redirect("https://blockstream.info/testnet/", 302)
    if chain == 'BTC':
        return redirect("https://blockstream.info/", 302)

@app.route("/chain/<chain>/block/<blockhash>")
def blockExplorer(chain, blockhash):
    if chain == 'TSR':
        return redirect(f"https://openchains.info/coin/tesseract/block/{blockhash}", 302)
    if chain == 'tBTC':
        return redirect(f"https://blockstream.info/testnet/block/{blockhash}", 302)
    if chain == 'BTC':
        return redirect(f"https://blockstream.info/block/{blockhash}", 302)  

@app.route("/chain/<chain>/tx/<txid>")
def txExplorer(chain, txid):
    if chain == 'TSR':
        return redirect(f"https://openchains.info/coin/tesseract/tx/{txid}", 302)
    if chain == 'tBTC':
        return redirect(f"https://blockstream.info/testnet/tx/{txid}", 302)
    if chain == 'BTC':
        return redirect(f"https://blockstream.info/tx/{txid}", 302)        

@app.route("/versions/xid/<xid>")
def xidVersions(xid):
    db = ScannerDb()
    latest = db.getLatestVersion(xid)
    versions = xidb.getVersions(latest)
    return render_template('versions.html', xid=xid, versions=versions)

@app.route("/versions/cid/<cid>")
def cidVersions(cid):
    db = ScannerDb()
    xid = xidb.getXid(cid)
    latest = db.getLatestVersion(xid)
    versions = xidb.getVersions(latest)
    return render_template('versions.html', xid=xid, versions=versions)

@app.route("/pin/xid/<xid>")
def pinVersions(xid):
    db = ScannerDb()
    latest = db.getLatestVersion(xid)
    versions = xidb.getVersions(latest)
    for version in versions:
        cid = version['cid']
        if xidb.pin(cid):
            flash(f"pinned {cid}")
        cid = version['auth_cid']
        if xidb.pin(cid):
            flash(f"pinned {cid}")
    return redirect(f"/versions/xid/{xid}")

@app.route("/authorize/<chain>", methods=['GET', 'POST'])
def authorize(chain):    
    form = TransferForm()

    if request.method == 'GET':
        return render_template('transfer.html', chain=chain, form=form)

    cid = form.cid.data

    if form.cancel.data or not cid:
        flash("authorization canceled")
        return redirect(f"/vault/{chain}")
        
    authorizer = Authorizer(chain)
    meta = xidb.getMeta(cid)

    if not form.confirm.data:
        authorizer.updateWallet()
        return render_template('transfer.html', confirm=True, form=form, meta=meta, authorizer=authorizer)

    if meta and xidb.pin(cid):
        txid = authorizer.authorize(cid)
        flash(f"authorized with txid {txid}")
    else:
        flash('authorization cancelled')

    return redirect(f"/vault/{chain}")

@app.route("/transfer/<chain>", methods=['GET', 'POST'])
def transfer(chain):
    form = TransferForm()

    if request.method == 'GET':
        return render_template('transfer.html', transfer=True, chain=chain, form=form)

    cid = form.cid.data
    addr = form.addr.data

    if form.cancel.data or not cid or not addr:
        flash("transfer canceled")
        return redirect(f"/vault/{chain}")

    authorizer = Authorizer(chain)
    meta = xidb.getMeta(cid)

    if not form.confirm.data:
        authorizer.updateWallet()
        return render_template('transfer.html', transfer=True, confirm=True, form=form, meta=meta, authorizer=authorizer)
    
    if meta and xidb.pin(cid):
        txid = authorizer.transfer(cid, addr)
        flash(f"transferred with txid {txid}")
    else:
        flash('transfer cancelled')
        
    return redirect(f"/vault/{chain}")

if __name__ == "__main__":
    db = ScannerDb()
    print(db.getAssets())
