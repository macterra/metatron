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

const ipfs = new ipfsClient({host:'localhost', port: '5001', protocol:'http'})
const app = express()

app.set('view engine','ejs')
app.use(bodyParser.urlencoded({extended:true}))
app.use(fileUpload())


app.get('/', (req,res) => {
    res.render('home')
    console.log('home hit')
    console.log(uuidv4())
    
    cid = 'QmTpkUxYfEXg1ZzFVYGr62P78HAGN9TSV1v6vMGp333vcv'
    resolveCid(cid)
})

app.post('/meta', (req, res) => {
    const cid = req.body.cid

    console.log('meta', cid)
    const resolve = resolveCid(cid)
    
    resolve.then(data => {
        console.log('certs', data.certs)
        console.log('orig', data.orig)
        rawcerts = JSON.stringify(data.certs,null,2);   
        res.render('meta', {cid, data, rawcerts})     
    })    
})

const getFile = async (cid) => {
    
    const chunks = []
    
    for await (const chunk of ipfs.cat(cid)) {
        chunks.push(chunk)
    }

    data = uint8ArrayConcat(chunks)
    content = uint8ArrayToString(data)

    return content
}

const getHead = async (xid) => {
    db = await fsp.readFile('db.json', 'utf8')
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
    
    meta = await getFile(cert.cid)
    meta = JSON.parse(meta)
    console.log('meta', meta)

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

app.listen(3000,'127.0.0.1', () => {
    console.log('Server is running on port 3000')
})