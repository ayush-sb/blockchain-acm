#%%
import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse

#%% Block & Blockchain

class Blockchain:
    
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.create_block(proof = 1, previous_hash = '0')
        self.nodes = set()

    def create_block(self, proof, previous_hash): # creates a new block, returns it and appends it to the blockchain
        block = {'index' : len(self.chain) + 1,
                 'timestamp' : str(datetime.datetime.now()),
                 'proof' : proof,
                 'previous_hash' : previous_hash,
                 'transactions' : self.transactions}
        
        self.transactions = []
        self.chain.append(block)
        return block

    def get_previous_block(self):
        return self.chain[-1]

    def proof_of_work(self, previous_proof): # finds the proof of work, initially = 1
        new_proof = 1
        check_proof = False
        
        while not check_proof: # proof of work = (n_p ^ 2) - (p_p ^ 2)
            buf = str(new_proof ** 2 - previous_proof ** 2).encode()    
            hash_operation = hashlib.sha256(buf).hexdigest()
            
            if hash_operation[ : 4] == "0000":
                check_proof = True
            
            else:
                new_proof += 1
        
        return new_proof

    def hash(self, block): # SHA256 in hex form
        encoded_block = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain): # check if all hashes are correct and all proofs start with '0000'
        previous_block = chain[0]
        block_index = 1
        
        while(block_index < len(chain)):
            block = chain[block_index]
            
            if(block['previous_hash'] != self.hash(previous_block)): # checking equality of hashes
                return False
            
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof ** 2 - previous_proof ** 2).encode()).hexdigest()
            
            if hash_operation[ : 4] != "0000": # checking if it starts with '0000'
                return False
            
            previous_block = block # update previous_block to current block for next iteration
            block_index += 1
        
        return True
    
    def add_transaction(self, sender, reciever, amount): # define transaction in proper format
        self.transactions.append({'sender' : sender,
                                  'reciever' : reciever,
                                  'amount' : amount})
        previous_block = self.get_previous_block()
        
        return previous_block['index'] + 1
    
    def add_node(self, address): # add a node to the list of nodes
        parsed_url = urlparse(address) # parse address into a URL
        self.nodes.add(parsed_url.netloc) # cannot use .append() for sets
    
    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        
        for node in network: # iterate over every node in network
            response = requests.get(f'http://{node}/get_chain') # f-string formatting
        
            if response.status_code == 200: # checking for OK code return
                length = response.json()['length']
                chain = response.json()['chain']
            
                if length > max_length and self.is_chain_valid(chain): # updating the longest chain and its length, after checking validity of the new chain
                    max_length = length
                    longest_chain = chain
        
        if longest_chain:
            self.chain = longest_chain
            return True
        
        return False

#%% Create address for node on port 5000

node_address = str(uuid4()).replace('-', '')

#%% Flask webapp and new object

app = Flask(__name__)
blockchain = Blockchain() # create new instance of Blockchain

#%% Mine new block

@app.route('/mine_block', methods = ['GET']) # setting up URL and get request

def mine_block():
    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    transactions = blockchain.add_transaction(sender = node_address, reciever = 'R2', amount = 1)
    
    block = blockchain.create_block(proof, previous_hash) # creating block
    
    response = {'message' : "New block has been mined.",
                'index' : block['index'],
                 'timestamp' : block['timestamp'],
                 'proof' : block['proof'],
                 'previous_hash ' : block['previous_hash'],
                 'transactions' : block['transactions']}
    
    return jsonify(response), 200

#%% Get full blockchain

@app.route('/get_chain', methods = ['GET'])

def get_chain():
    response = {'chain' : blockchain.chain,
                'length' : len(blockchain.chain)}
    
    return jsonify(response), 200

#%% Check validity

@app.route('/is_valid', methods = ['GET'])

def is_valid():
    bc = blockchain.chain
    flag = blockchain.is_chain_valid(bc)
    
    if(flag):
        response = {'message' : "Blockchain is valid."}
        
    else:
        response = {'message' : "Blockchain is invalid."}
    
    return jsonify(response), 200

#%% Add a transaction to block

@app.route('/add_transaction', methods = ['POST'])

def add_transaction():
    json = request.get_json()
    transaction_keys = ['sender', 'reciever', 'amount']
    
    if not all (key in json for key in transaction_keys):
        return 'Some transaction elements missing.', 400
    
    index = blockchain.add_transaction(json['sender'], json['reciever'], json['amount'])
    response = {'message' : f'This transaction will be added to block {index}.'}
    
    return jsonify(response), 201


#%% Connect new nodes to network

@app.route('/connect_node', methods = ['POST'])

def connect_node():
    json = request.get_json()
    nodes = json.get('nodes')
    
    if nodes is None:
        return "No node.", 400
    
    for node in nodes:
        blockchain.add_node(node)
    
    response = {'message' : 'All nodes are connected.',
                'total_nodes' : list(blockchain.nodes)}
    
    return jsonify(response), 201

#%% Replace chain by longest chain if needed

@app.route('/replace_chain', methods = ['GET'])

def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    
    if is_chain_replaced:
        response = {'message': 'Chain has been replaced by the longest one.',
                    'new_chain': blockchain.chain}
    
    else:
        response = {'message': 'Chain is already longest one.',
                    'actual_chain': blockchain.chain}
    
    return jsonify(response), 200

#%% Run application

app.run(host='0.0.0.0', port = 5000)