from flask import Flask, render_template, redirect, request, flash
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from authorize import *

class AuthorizeForm(FlaskForm):
        cid = StringField('cid')
        submit = SubmitField('authorize')

# class ConfirmForm(FlaskForm):
#         submit = SubmitField('confirm')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

#print(app.config)

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
    blockchain = AuthServiceProxy(connect, timeout=120)
    authorizer = Authorizer(blockchain)
    authorizer.updateWallet()
    balance = authorizer.balance
    meta = getMeta(cid)

    if request.method == 'POST':
        if meta and request.form.get('confirm', 'Cancel') == 'Confirm':
            flash('confirmed')
        else:
            flash('cancelled')
        return redirect(f"/wallet/{chain}")

    return render_template('confirm.html', cid=cid, meta=meta, balance=balance, txfee=txfee)


