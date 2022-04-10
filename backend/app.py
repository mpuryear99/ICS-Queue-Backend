from platform import machine
from pprint import pprint
from flask import Flask, redirect, url_for, request
from pymongo import MongoClient
from flask_cors import CORS
import json
import os
import time
from dotenv import load_dotenv
from bson import ObjectId

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

load_dotenv(dotenv_path='./config.env')
ATLAS_URI = os.environ.get('ATLAS_URI')
client = MongoClient(ATLAS_URI)


db = client['ics_scheduler']
machines_col = db['machines']
appt_col = db['appointments']

# returns desired machine based on name
@app.route('/machines/<id>', methods=['GET'])
def getmachine(id):
    data = machines_col.find_one({'_id':ObjectId(id)})
    if data != None:
        data['_id'] = str(data['_id'])
        print(data)
        return data

# returns all the machines in the database
@app.route('/machines/', methods=['GET'])
def getmachines():
    data = []
    for m in machines_col.find({}):
        print(m)
        m['_id'] = str(m['_id'])
        print(m)
        data.append(m)
    return json.dumps(data)

# add a machine to the database
@app.route('/machines/add', methods=['POST'])
def addmachine():
    pass

# deletes machine from database
@app.route('/machines/<id>/delete', methods=['DELETE'])
def deletemachine(id):
    pass

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
    
    res = appt_col.insert_one(data)
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
    for a in appt_col.find({"startTime": {"$gte": now, "$lt": nextWeek}}):
        a['_id'] = str(a['_id'])
        data.append(a)
    return json.dumps(data)

# Returns all appointments 
# example request: GET http://127.0.0.1:5000/getallappointments/
@app.route('/getallappointments/', methods=['GET'])
def getallappointments():
    data = []
    for a in appt_col.find({"_id": {"$gte": 0}}):
        a['_id'] = str(a['_id'])
        data.append(a)
    return json.dumps(data)


# ~~~~~~ helper functions ~~~~~~
# These are functions that help in the back-end and cannot be accessed by front-end

# helper function to add machines to database using specified file
def addmachines(fn):
    js = json.load(open(fn))

    res = machines_col.insert_many(js['machines'])
    return json.dumps(res)

# update a machine's name
def updatemachinename(id, name):
    machines_col.update_one({"_id": ObjectId(id)}, {"$set": {"name": name}})

# update a machine description
def updatedescription(id, description):
    machines_col.update_one({"_id": ObjectId(id)}, {"$set": {"description": description}})

# update the image path for a machine
def updateimagepath(id, imagePath):
    machines_col.update_one({"_id": ObjectId(id)}, {"$set": {"image": path}})



if __name__ == "__main__":
    app.run(host='127.0.0.1', debug=True, port=5000)
