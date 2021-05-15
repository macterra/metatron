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
    host: process.env.DB_HOST,
    port: 6379
})

client.on('error', err => {
    console.log('Error ' + err);
})

const app = express()

app.set('view engine','ejs')
app.use(bodyParser.urlencoded({extended:true}))
app.use(fileUpload())

app.get('/', (req, res) => {
    getCerts().then(certs => {
        status = JSON.stringify(certs, null, 2)
        res.render('home', {certs})
    })
})

app.get('/status', (req, res) => {
    getStatus().then(status => {
        status = JSON.stringify(status, null, 2)
        res.render('status', {status})
    })
})

app.get('/cid/:cid', (req, res) => {
    console.log(req.params.cid)
    const cid = req.params.cid

    console.log('meta', cid)
    const resolve = resolveCid(cid)
    
    resolve.then(data => {
        console.log('certs', data.certs)
        console.log('orig', data.orig)
        rawcerts = JSON.stringify(data.certs, null, 2)
        res.render('meta', {cid, data, rawcerts})     
    })    
})

const getStatus = async () => {
    status = {}

    keys = await client.keysAsync("scanner/*")
    console.log(keys)
        
    for (const key of keys.sort()) {
        val = await client.getAsync(key)
        status[key] = val
        console.log(key, val)
    }

    return status
}

const getCerts = async () => {
    certs = []

    keys = await client.keysAsync("xid/*")
    console.log(keys)

    for (const key of keys.sort()) {
        val = await client.getAsync(key)
        certs.push(val)
    }

    return certs
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
    const ipfs = new ipfsClient({host: process.env.IPFS_HOST, port: '5001', protocol:'http'})

    cid = cid.trim()
    
    for await (const chunk of ipfs.cat(cid)) {
        chunks.push(chunk)
    }

    data = uint8ArrayConcat(chunks)
    content = uint8ArrayToString(data)

    return content
}

const isDirectory = async (cid) => {
    const ipfs = new ipfsClient({host: process.env.IPFS_HOST, port: '5001', protocol:'http'})

    cid = cid.trim()

    status = await ipfs.files.stat('/ipfs/' + cid)

    console.log('stat', status)

    return status.type === 'directory'
}

const resolveCid = async (cid) => {

    isDir = await isDirectory(cid)

    if (isDir) {
        meta = cid.trim() + '/meta.json'
    }
    else {
        meta = cid.trim()
    }

    console.log('resolveCid', meta)
    orig = await getFile(meta)
    orig = JSON.parse(orig)
    console.log('xid', orig.xid)

    head = await client.getAsync('xid/' + orig.xid)
    console.log('head:', head)
    
    cert = await getFile(head)
    cert = JSON.parse(cert)
    console.log('head cert', cert)
    console.log('head cid', cert.cid)
    
    certs = [ cert ]

    while (cert.prev) {
        data = await getFile(cert.prev)
        cert = JSON.parse(data)
        certs.push(cert)
    }

    console.log('certs:', certs)

    for (const cert of certs.reverse()) {
        console.log(cert.version, cert.cid, cert.auth.time, cert.auth.id)
    }

    return {
        "orig": orig,
        "certs": certs
    }
}

app.listen(3000,'0.0.0.0', () => {
    console.log('Server is running on port 3000')
})