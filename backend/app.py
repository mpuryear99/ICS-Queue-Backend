from pprint import pprint
from flask import Flask, redirect, url_for
from pymongo import MongoClient
from flask_cors import CORS
import json
import os
from dotenv import load_dotenv
from bson import json_util

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

load_dotenv(dotenv_path='./config.env')
ATLAS_URI = os.environ.get('ATLAS_URI')
client = MongoClient(ATLAS_URI)


db = client['ics_scheduler']
machines = db['machines']

# returns desired machine based on name
@app.route('/getmachine/<name>', methods=['GET'])
def getmachine(name):
    data = machines.find_one({'name':name})
    if data != None:
        data['_id'] = str(data['_id'])
        return data

# returns all the machines in the database
@app.route('/getmachines/', methods=['GET'])
def getmachines():
    data = []
    for m in machines.find({}):
        print(m)
        m['_id'] = str(m['_id'])
        print(m)
        data.append(m)
    return json.dumps(data)

# adds machines to database using specified file
@app.route('/addmachines/<name>', methods=['POST'])
def addmachines(fn):
    db = client['ics_scheduler']
    col = db['machines']
    js = json.load(open(fn))
    res = col.insert_many(js['machines'])
    return json.dumps(res)


if __name__ == "__main__":
    app.run(debug=True)

