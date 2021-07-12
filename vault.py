import os
import redis
import xidb

from flask import Flask, render_template, redirect, request, flash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from authorize import *
from urllib.parse import urlparse

class AuthorizeForm(FlaskForm):
    cid = StringField('cid')
    submit = SubmitField('authorize')

class TransferForm(FlaskForm):
    cid = StringField('cid')
    addr = StringField('address')
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

@app.route("/explorer")
def explorer():
    return render_template('explorer.html', assets=getAssets())

@app.route("/scanner")
def scanner():
    return render_template('scanner.html', status=getStatus())

@app.route("/reset")
def resetDb():
    db = getDb()
    db.flushall()
    return redirect("/scanner")

@app.route("/vault/<chain>")
def vault(chain):    
    connect=os.environ.get(f"{chain}_CONNECT")
    print(f"connect={connect}")
    blockchain = AuthServiceProxy(connect, timeout=10)
    authorizer = Authorizer(blockchain)
    authorizer.updateWallet()
    txurl='https://openchains.info/coin/tesseract/tx/'
    return render_template('vault.html', chain=chain, txurl=txurl, authorizer=authorizer)

@app.route("/receive/<chain>")
def receive(chain):    
    connect=os.environ.get(f"{chain}_CONNECT")
    print(f"connect={connect}")
    blockchain = AuthServiceProxy(connect, timeout=10)
    authorizer = Authorizer(blockchain)
    addr = authorizer.getAddress()
    flash(f"receive address: {addr}")
    return redirect(f"/vault/{chain}")

@app.route("/pin/chain/<chain>")
def pinAssets(chain):    
    connect=os.environ.get(f"{chain}_CONNECT")
    print(f"connect={connect}")
    blockchain = AuthServiceProxy(connect, timeout=10)
    authorizer = Authorizer(blockchain)
    authorizer.updateWallet()
    for asset in authorizer.assets:
        if xidb.pin(asset.cid):
            flash(f"pinned {asset.cid}")
    return redirect(f"/vault/{chain}")

@app.route("/auth/<cid>")
def auth(cid):
    cert = getMeta(cid)
    chain = cert['chain']['ticker']

    if chain == 'TSR':
        # get from config
        block_url = 'https://openchains.info/coin/tesseract/block/'
        tx_url = 'https://openchains.info/coin/tesseract/tx/'

    return render_template('auth.html', cid=cid, cert=cert, block_url=block_url, tx_url=tx_url)

@app.route("/ipfs/<path:path>")
def ipfs(path):
    o = urlparse(request.base_url)
    return redirect(f"http://{o.hostname}:8080/ipfs/{path}", 302)

@app.route("/versions/xid/<xid>")
def xidVersions(xid):
    latest = getLatestVersion(xid)
    versions = getVersions(latest)
    return render_template('versions.html', xid=xid, cid=cid, versions=versions)

@app.route("/versions/cid/<cid>")
def cidVersions(cid):
    xid = getXid(cid)
    latest = getLatestVersion(xid)
    versions = getVersions(latest)
    return render_template('versions.html', xid=xid, cid=cid, versions=versions)

@app.route("/pin/xid/<xid>")
def pinVersions(xid):
    latest = getLatestVersion(xid)
    versions = getVersions(latest)
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
    form = AuthorizeForm()
    if form.validate_on_submit():         
        return redirect(f"/authorize/{chain}/{form.cid.data}")
    return render_template('authorize.html', form=form)

@app.route("/authorize/<chain>/<cid>", methods=['GET', 'POST'])
def authorize2(chain, cid):
    #print('authorize2', request.method, chain, cid)
    connect=os.environ.get(f"{chain}_CONNECT")
    blockchain = AuthServiceProxy(connect, timeout=10)
    authorizer = Authorizer(blockchain)
    authorizer.updateWallet()
    balance = authorizer.balance
    meta = getMeta(cid)

    if request.method == 'POST':
        ok = request.form.get('confirm', 'Cancel') == 'Confirm'
        if ok and meta and xidb.pin(cid):
            txid = authorizer.authorize(cid)
            flash(f"authorized with txid {txid}")
        else:
            flash('authorization cancelled')
        return redirect(f"/vault/{chain}")

    return render_template('confirm.html', cid=cid, meta=meta, balance=balance, txfee=txfee)

@app.route("/transfer/<chain>")
def transfer(chain):
    form = TransferForm()
    return render_template('transfer.html', chain=chain, form=form)

@app.route("/transfer/confirm/<chain>", methods=['POST'])
def transferConfirm(chain):
    form = TransferForm()

    cid = form.cid.data
    addr = form.addr.data

    if form.cancel.data or not cid or not addr:
        flash("transfer canceled")
        return redirect(f"/vault/{chain}")

    print('transferConfirm', request.method, chain, cid, addr)
    connect=os.environ.get(f"{chain}_CONNECT")
    blockchain = AuthServiceProxy(connect, timeout=10)
    authorizer = Authorizer(blockchain)
    authorizer.updateWallet()
    balance = authorizer.balance
    meta = getMeta(cid)

    return render_template('transferConfirm.html', chain=chain, form=form, cid=cid, addr=addr, meta=meta, balance=balance, txfee=txfee)

@app.route("/transfer/exec/<chain>", methods=['POST'])
def transferExec(chain):
    form = TransferForm()

    if form.cancel.data:
        flash("transfer canceled")
        return redirect(f"/vault/{chain}")

    cid = form.cid.data
    addr = form.addr.data
    print('send3', chain, cid, addr)
    flash("transfer txid...")

    return redirect(f"/vault/{chain}")

def getDb():
    dbhost = os.environ.get('DB_HOST')

    if not dbhost:
        dbhost = 'localhost'
    
    return redis.Redis(host=dbhost, port=6379, db=0)

def getStatus():
    db = getDb()
    keys = db.keys("scanner/*")

    status = {}

    for key in keys:
        val = db.get(key)
        _, chain, prop = key.decode().split('/')
        if not chain in status:
            status[chain] = {}
        status[chain][prop] = val.decode()

    return status

def getLatestVersion(xid):
    db = getDb()
    latest = db.get(f"xid/{xid}")
    
    if latest:
        latest = latest.decode().strip()

    return latest

def getAssets():
    db = getDb()
    xids = db.keys("xid/*")
    print(xids)

    assets = []

    for xid in xids:
        cid = db.get(xid).decode().strip()
        print(xid, cid)
        version = xidb.getMeta(cid)
        if version:
            meta = xidb.getMeta(version['cid'])
            if 'asset' in meta:
                version['meta'] = meta
                assets.append(version)
            else:
                print("deprecated", xid)
                #db.delete(xid)

    return sorted(assets, key=lambda version: version['meta']['asset'])

if __name__ == "__main__":
    print(getAssets())
