export FLASK_APP=vault
export FLASK_ENV=development
export BTC_CONNECT="http://scully:sw33tp0tat0@btc.metagamer.org:8332"
export tBTC_CONNECT="http://scully:sw33tp0tat0@btc.metagamer.org:18332"
export TSR_CONNECT="http://scully:sw33tp0tat0@btc.metagamer.org:18331"
export SECRET_KEY='scully:sw33tp0tat0'

flask run --port=3001

#python3 vault.py
