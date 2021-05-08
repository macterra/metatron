const ipfsClient = require('ipfs-http-client')
const express = require('express')
const bodyParser = require('body-parser')
const fileUpload = require('express-fileupload')
const fs = require('fs')
const fsp = require('fs').promises
const CID = require('cids')
const uint8ArrayConcat = require('uint8arrays/concat')
const uint8ArrayToString = require('uint8arrays/to-string')
const { v4: uuidv4 } = require('uuid')
const redis = require('redis')
const { promisifyAll } = require('bluebird');

promisifyAll(redis);

const client = redis.createClient({
    host: 'localhost',
    port: 6379
})

client.on('error', err => {
    console.log('Error ' + err);
})

const app = express()

app.set('view engine','ejs')
app.use(bodyParser.urlencoded({extended:true}))
app.use(fileUpload())

app.get('/', (req,res) => {
    db = "TBD"
    res.render('home', {db})

    // console.log('home hit')
    // console.log(uuidv4())
    
    // cid = 'QmTpkUxYfEXg1ZzFVYGr62P78HAGN9TSV1v6vMGp333vcv'
    // resolveCid(cid)
})

app.get('/status', (req,res) => {
    getStatus().then(status => {
        status = JSON.stringify(status, null, 2)
        res.render('status', {status})
    })
})

const getStatus = async () => {
    keys = await client.keysAsync("scanner/*")
    console.log(keys)

    status = {}
        
    for (const key of keys.sort()) {
        val = await client.getAsync(key)
        status[key] = val
        console.log(key, val)
    }

    return status
}

app.post('/meta', (req, res) => {
    const cid = req.body.cid

    console.log('meta', cid)
    const resolve = resolveCid(cid)
    
    resolve.then(data => {
        console.log('certs', data.certs)
        console.log('orig', data.orig)
        rawcerts = JSON.stringify(data.certs, null, 2)
        res.render('meta', {cid, data, rawcerts})     
    })    
})

const getFile = async (cid) => {
    
    const chunks = []    
    const ipfs = new ipfsClient({host:'localhost', port: '5001', protocol:'http'})

    cid = cid.trim()
    
    for await (const chunk of ipfs.cat(cid)) {
        chunks.push(chunk)
    }

    data = uint8ArrayConcat(chunks)
    content = uint8ArrayToString(data)

    return content
}

const getDb = async () => {
    db = await fsp.readFile('data/db.json', 'utf8')
    return JSON.parse(db)
}

const getHead = async (xid) => {
    db = await fsp.readFile('data/db.json', 'utf8')
    db = JSON.parse(db)

    console.log(db)

    return db[xid]
}

const resolveCid = async (cid) => {
    orig = await getFile(cid)
    orig = JSON.parse(orig)
    console.log('xid', orig.xid)

    head = await getHead(orig.xid)
    console.log('head:', head)
    
    cert = await getFile(head)
    cert = JSON.parse(cert)
    console.log('head cert', cert)
    console.log('head cid', cert.cid)
    
    // meta = await getFile(cert.cid)
    // meta = JSON.parse(meta)
    // console.log('meta', meta)

    certs = [ cert ]

    while (cert.prev) {
        data = await getFile(cert.prev)
        cert = JSON.parse(data)
        certs.push(cert)
    }

    console.log('certs:', certs)

    for (const cert of certs.reverse()) {
        console.log(cert.version, cert.time, cert.cid)
    }

    return {
        "orig": orig,
        "certs": certs
    }
}

app.listen(3000,'0.0.0.0', () => {
    console.log('Server is running on port 3000')
})