import os
import redis
import xidb

from flask import Flask, render_template, redirect, request, flash
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from authorize import *

class AuthorizeForm(FlaskForm):
        cid = StringField('cid')
        submit = SubmitField('authorize')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

#print(app.config)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/explorer")
def explorer():
    certs = getCerts()
    #print(certs)
    return render_template('explorer.html', certs=certs)

@app.route("/vault/<chain>")
def vault(chain):    
    connect=os.environ.get(f"{chain}_CONNECT")
    print(f"connect={connect}")
    blockchain = AuthServiceProxy(connect, timeout=10)
    height = blockchain.getblockcount()
    print(f"height={height}")
    authorizer = Authorizer(blockchain)
    authorizer.updateWallet()
    return render_template('vault.html', chain=chain, authorizer=authorizer)

@app.route("/meta/<cid>")
def meta(cid):
    meta = getMeta(cid)
    #return render_template('meta.html', cid=cid, meta=meta)
    if not meta:
        meta = "error: metadata not found"
    print(meta)
    return meta

@app.route("/versions/<cid>")
def versions(cid):
    versions = getVersions(cid)
    return render_template('versions.html', cid=cid, versions=versions)

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
        if meta and request.form.get('confirm', 'Cancel') == 'Confirm':
            txid = authorizer.authorize(cid)
            flash(f"authorized with txid {txid}")
        else:
            flash('authorization cancelled')
        return redirect(f"/vault/{chain}")

    return render_template('confirm.html', cid=cid, meta=meta, balance=balance, txfee=txfee)

def getCerts():
    dbhost = os.environ.get('SCANNER_DBHOST')

    if not dbhost:
        dbhost = 'localhost'
    
    db = redis.Redis(host=dbhost, port=6379, db=0)
    xids = db.keys("xid/*")
    #print(xids)

    certs = []

    for xid in xids:
        cid = db.get(xid).decode().strip()
        cert = xidb.getCert(cid)
        if cert:
            meta = xidb.getMeta(cert['cid'])
            if 'asset' in meta:
                cert['meta'] = meta
                cert['cert'] = cid
                certs.append(cert)
            else:
                print("deprecated", xid)
                db.delete(xid)

    return certs

def test1():
    connect=os.environ.get(f"TSR_CONNECT")
    print(f"connect={connect}")
    blockchain = AuthServiceProxy(connect, timeout=10)
    height = blockchain.getblockcount()
    print(f"height={height}")
    authorizer = Authorizer(blockchain)
    authorizer.updateWallet()

def test2():
    dbhost = os.environ.get('SCANNER_DBHOST')

    if not dbhost:
        dbhost = 'localhost'
    
    db = redis.Redis(host=dbhost, port=6379, db=0)
    xids = db.keys("xid/*")
    print(xids)
    for xid in xids:
        cid = db.get(xid).decode().strip()
        print(xid, cid)
        meta = getMeta(cid)
        print(meta)
        if not meta:
            db.delete(xid)
        else:
            prev = meta['prev']
            vers = meta['version']
            print(vers, prev)
            while prev:
                meta = getMeta(prev)
                prev = meta['prev']
                vers = meta['version']
                print(vers, prev)


if __name__ == "__main__":
    test2()
