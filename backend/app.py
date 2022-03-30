from pprint import pprint
from flask import Flask, redirect, url_for, request
from pymongo import MongoClient
from flask_cors import CORS
import json
import os
import time
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
appointments = db['appointments']

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

# adds a single appointment to the database
# example request: POST http://127.0.0.1:5000/addappointment/?name=Tyler&machineID=123&startTime=456&endTime=789
@app.route('/addappointment/', methods=['POST'])
def addappointment():
    recieved = request.args.to_dict()

    data = {
        'name': recieved['name'],
        'machineID': int(recieved['machineID']),
        'startTime': float(recieved['startTime']),
        'endTime': float(recieved['endTime'])
    }
    print("data: ", data)
    
    res = appointments.insert_one(data)
    return str(res.inserted_id)
    

# Returns all appointments within the week
# example request: GET http://127.0.0.1:5000/getweekappointments/
@app.route('/getweekappointments/', methods=['GET'])
def getweekappointments():
    data = []
    now = time.time()
    nextWeek = now + 604800 # 604800 seconds in a week
    print(now)
    # finds appointments between now and one week from now
    for a in appointments.find({"startTime": {"$gte": now, "$lt": nextWeek}}):
        a['_id'] = str(a['_id'])
        data.append(a)
    return json.dumps(data)


if __name__ == "__main__":
    app.run(debug=True)

