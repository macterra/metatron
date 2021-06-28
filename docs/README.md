# Metatron

## The Extensible Identifier (xid)

The system provides a way to establish ownership of 128-bit random numbers called `xid` (for eXtensible IDentifier)

The value of the xid must be a random [UUID](https://en.wikipedia.org/wiki/Universally_unique_identifier)
- any UUID that can be compressed by zlib to less than its original length of 16 bytes will be considered invalid
- the xid should be a pure indexical, it should be able to point to any digital content without bias, including nothing in the case it is retired or disabled
- therefore the xid should contain no internal information (though it is always possible to encode encrypted information via the UUID5 standard)

The xid is associated with digital content by mapping it to a content identifier (CID) on IPFS
- if the CID resolves to a file, the file must be a JSON file with a top-level property named `xid`
- if the CID resolves to a directory, it must have a top-level file named `xid` that contains the xid
- if the CID resolves to a IPLD node, it must have a top-level property named `xid`

## Rules of ownership 

### Precedence

- blockchain agnostic, precedence by block time
- testnet claims are provisional and may be overridden by any mainnet
- every metatron node may decide which blockchains to scan
    - this means that a node that scans only bitcoin may not recognize the ownership claims submitted to RavenCoin for example
    - let the market decide which blockchains should be used for this purpose

### Bitcoin-derived blockchains
- ownership claims are submitted in special txns called auth txns (short for authorization transactions)
- the auth txn must contain one unspendable nulldata txo encoding IPFS CID (v0 or v1 multihash)
- the auth txn must contain one spendable txo with a (magic) value of "0.00001111" that establishes ownership of the metadoc
    - sufficiently low valued transactions are prohibited by the bitcoin consensus as "dust" because it costs more in transaction fees to spend them than they are worth
    - since we need a positive value we might as well use it to distinguish auth txos
        - the relatively low value was selected deliberately to minimize value locked up in ownership claims
        - and also to make it unlikely that these txos will randomly be selected to cover fees
    - in order to update the metadoc for a given xid, a subsequent auth txn MUST spend the previous auth txo (this is the essential key to the whole system)
        - anyone can copy and publish a new version of the metadoc, it is public information
        - only the owner can publish an authorized revision
    - the txn will necessarily contain additional inputs and outputs to cover blockchain fees
    - it is the responsibility of the authorization software to ensure that auth txos are used only to update ownership claims, not for fees

### Operation

The system scans new blocks for auth transactions, validates them, generates block certificates (block-certs) for valid ones, and updates the version database. Instances of the system that implement that same consensus rules and scan the same set of blockchains will necessarily converge on the same version database state analogously to the unspent transaction output (UTXO) set for a particular blockchain.

![](diagrams/versions.png)

1. The first version of a document (or [image](diagrams/verified-versions-v1.png)) is created and added to IPFS. 
2. A [metadata document](meta-v0.json) references the CID of the doc v1. A random `idx` is generated for this object. It is the only property that must remain constant for the life of the object.
3. The first version is authorized by submitting an auth txn to a blockchain. The txn references the CID of the metadoc.
4. A blockchain scanner discovers the auth txn when it is confirmed on a block. The metadoc will be resolved from its CID on IPFS. The scanner will search its db for the idx in the metadoc but it won't be found since it is new. The scanner can confirm that the transaction inputs referenced in the auth txn are not auth txns. The first version of the block certification [block-cert](block-cert-v0.json) is created and added to IPFS. The idx is mapped to the CID of the block-cert in the db.
5. The author creates a new revision of the [image](diagrams/verified-versions-v2.png), doc v2.
6. The system updates the [metadoc](meta-v1.json) referencing the CID of the v2 of the doc and the CID of v1 of the metadoc. 
7. The second version is authorized by submitting an auth txn to the blockchain that references the CID of v2 of the metadoc and spends the the UTXO from the first auth txn.
8. The blockchain scanner discovers the v2 auth txn when it is confirmed on a block. Again it finds the idx by resolving the metadoc from IPFS. This time it finds the idx in the db mapped to the first block-cert. The scanner can confirm that the new auth txn spends the auth txn referenced in the block-cert. If everything checks out a new [block-cert](block-cert-v1.json) is created and added to IPFS. The db is updated so that idx is now mapped to the new block-cert.
9. The process is repeated for a 3rd version of the [image](diagrams/verified-versions-v3.png)
10. A new [metadoc](meta-v2.json) is created and added to IPFS.
11. An auth txn is submitted that references the new metadoc and spends the txo from the last auth txn.
12. The scanner discovers the new auth txn on the blockchain, verifies all the references are valid, creates a new [block-cert](block-cert-v3.json), adds it to IPFS, and updates the db so that the idx is mapped to the latest version.
