from platform import machine
from pprint import pprint
from typing import Dict
from flask import Flask, redirect, url_for, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS
import json
import os
import time
from dotenv import load_dotenv
from bson import ObjectId
from http import HTTPStatus

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

dotenv_path = os.path.join(os.path.dirname(__file__), "config.env")
load_dotenv(dotenv_path=dotenv_path)
ATLAS_URI = os.environ.get('ATLAS_URI')
client = MongoClient(ATLAS_URI)


db = client['ics_scheduler']
machines_col = db['machines']
appt_col = db['appointments']
users_col = db['users']


# ~~~~~~ MACHINES ~~~~~~

# Returns desired machine based on name
@app.route('/machines/<id>', methods=['GET'])
def getmachine(id):
    data = machines_col.find_one({'_id':ObjectId(id)})
    if data is None:
        return "Machine not found", HTTPStatus.NOT_FOUND
    data['_id'] = str(data['_id'])
    print(data)
    return jsonify(data)

# Returns all the machines in the database
@app.route('/machines', methods=['GET'])
def getmachines():
    data = []
    for m in machines_col.find({}):
        m['_id'] = str(m['_id'])
        data.append(m)
    return jsonify(data)

# Add a machine to the database
# Machine structure in the database:
# machine {
#     _id,
#     name,
#     image,
#     description
# }
@app.route('/machines/add', methods=['POST'])
def addmachine():
    recv = request.args.to_dict()

    m = {
        "name": recv['name'],
        "image": recv['image'],
        "description": recv['description']
    }
    try:
        m['description'] = m['description'].strip().capitalize()
    except Exception as e:
        print(e)
    print(m)
    res = machines_col.insert_one(m)
    return str(res.inserted_id)

# adds a machine to database using json data
@app.route('/machines/add/post', methods=['POST'])
def addmachinespost():
    received = request.get_json()
    print(received)

    data = ['name','image','description']
    
    for key in received.keys():
        print(key)
        if key == 'description':
            try:
                received['description'] = received['description'].strip().capitalize()
            except Exception as e:
                print(e)
        elif key == 'name':
            pass
        elif key == 'image':
            pass
        else:
            return f"Invalid key: {key}", HTTPStatus.BAD_REQUEST

    res = machines_col.insert_one(received)
    return res


# Deletes machine from database
@app.route('/machines/<id>/delete', methods=['DELETE'])
def deletemachine(id):
    res = machines_col.delete_one({"_id": ObjectId(id)})
    return str(res.deleted_count)


# ~~~~~~ APPOINTMENTS ~~~~~~

# adds a single appointment to the database
# example request: POST http://127.0.0.1:5000/appointments/add/?name=Tyler&machineID=123&startTime=456&endTime=789
# appointment structure in database:
# appointment {
#     _id,
#     user_id,
#     machine_id,
#     username,
#     startTime,
#     endTime
# }
@app.route('/appointments/add', methods=['POST'])
def addappointment():
    recieved = request.args.to_dict()

    data = {
        'user_id': ObjectId(recieved['user_id']),
        'machine_id': ObjectId(recieved['machine_id']),
        'username': recieved['username'],
        'startTime': int(recieved['startTime']),
        'endTime': int(recieved['endTime'])
    }
    print("data: ", data)
    
    # try to insert the appointment into appointment collection
    res = appt_col.insert_one(data)
    if not ObjectId.is_valid(res.inserted_id):
        return "Insertion failed", HTTPStatus.INTERNAL_SERVER_ERROR

    return str(res.inserted_id)

# adds an appointment when given json data
@app.route('/appointments/add/post', methods=['POST'])
def addappointmentpost():
    received: Dict[str] = request.get_json()
    print(received)

    req_keys = {'user_id','machine_id','username','startTime','endTime'}

    data = {}
    for key,value in received.items():
        if key not in req_keys:
            continue
        
        if key == "user_id":
            value = ObjectId(str(value))
            user = users_col.find_one({'_id':value})
            if user is None:
                return "User does not exist", HTTPStatus.BAD_REQUEST
        elif key == "machine_id":
            value = ObjectId(str(value))
            machine = machines_col.find_one({'_id':value})
            if machine is None:
                return "Machine does not exist", HTTPStatus.BAD_REQUEST
        elif key == 'username':
            value = str(value)
        elif key == 'startTime':
            value = int(value)
        elif key == 'endTime':
            value = int(value)
        
        data[key] = value
    
    if len(req_keys):
        return f"Missing keys: {req_keys}", HTTPStatus.BAD_REQUEST

    # try to insert the appointment into appointment collection
    res = appt_col.insert_one(received)
    if not ObjectId.is_valid(res.inserted_id):
        return "Insertion failed", HTTPStatus.INTERNAL_SERVER_ERROR

    # add appointment to user's appointments array
    # user = users_col.update_one({"_id": ObjectId(received['user_id'])}, {"$push": {"appointments": res.inserted_id}})
    # if user.upserted_id == None:
    #     return "Update failed"

    return str(res.inserted_id), HTTPStatus.CREATED


# Returns all appointments that fit query based on start/end time ranges and associated _ids.
# Example request: 
#   GET http://127.0.0.1:5000/appointments/query
#           ?startBefore=float
#           &startAfter=float
#           &endBefore=float
#           &endAfter=float
#           &machine_id=str
#           &user_id=str
#           &checkOnly
#           $count
# All parameters are optional. Param `checkOnly` overrides `count`.
# Param `count` returns number of objects matching query.
# Param `checkOnly` overrides `count` and returns True/False result of count > 0.
# All returns are json.
@app.route('/appointments/query', methods=['GET'])
def getappointmentbyquery():
    received = request.args.to_dict()

    startBefore = received.get('startBefore', None)
    startAfter  = received.get('startAfter', None)
    endBefore   = received.get('endBefore', None)
    endAfter    = received.get('endAfter', None)
    machine_id  = received.get('machine_id', None)
    user_id     = received.get('user_id', None)
    checkOnly   = received.get('checkOnly', None) is not None
    getCount    = received.get('count', None) is not None

    findParams = {}
    if (startBefore is not None):
        p = findParams.setdefault('startTime', {})
        p['$lte'] = float(startBefore)
    if (startAfter is not None):
        p = findParams.setdefault('startTime', {})
        p['$gte'] = float(startAfter)
    if (endBefore is not None):
        p = findParams.setdefault('endTime', {})
        p['$lte'] = float(endBefore)
    if (endAfter is not None):
        p = findParams.setdefault('endTime', {})
        p['$gte'] = float(endAfter)
    if (machine_id is not None):
        findParams['machine_id'] = ObjectId(machine_id)
    if (user_id is not None):
        findParams['user_id'] = ObjectId(user_id)

    if (checkOnly):
        exists = False
        for a in appt_col.find(findParams):
            exists = True
            break
        return jsonify(exists)

    if (getCount):
        count = appt_col.count_documents(findParams)
        return jsonify(count)

    data = []
    for a in appt_col.find(findParams):
        a['_id'] = str(a['_id'])
        a['user_id'] = str(a['user_id'])
        a['machine_id'] = str(a['machine_id'])
        data.append(a)
    return jsonify(data)

# Returns all appointments 
# example request: GET http://127.0.0.1:5000/appointments/
@app.route('/appointments', methods=['GET'])
def getallappointments():
    data = []
    for a in appt_col.find({}):
        a['_id'] = str(a['_id'])
        a['user_id'] = str(a['user_id'])
        a['machine_id'] = str(a['machine_id'])
        data.append(a)
    return jsonify(data)

# Returns information about an appointment based on its ID
@app.route('/appointments/<id>', methods=['GET'])
def getappointment(id):
    data = appt_col.find_one({'_id':ObjectId(id)})
    if data is None:
        return "Appointment not found", HTTPStatus.NOT_FOUND
    data['_id'] = str(data['_id'])
    data['user_id'] = str(data['user_id'])
    data['machine_id'] = str(data['machine_id'])
    print(data)
    return jsonify(data)

# Deletes an appointment based on its ID
@app.route('/appointments/<id>/delete', methods=['DELETE'])
def deleteappointment(id):
    res = appt_col.delete_one({"_id": ObjectId(id)})
    return str(res.deleted_count)


# ~~~~~~ USERS ~~~~~~

# Returns all the users
@app.route('/users')
def getusers():
    data = []
    for u in users_col.find({}):
        u['_id'] = str(u['_id'])
        data.append(u)
    return jsonify(data)

# Return user count
@app.route('/usercount')
def getusercount():
    count = users_col.estimated_document_count()
    return jsonify(count)

# Return a user based on id
@app.route('/users/<id>', methods=['GET'])
def getuser(id):
    data = users_col.find_one({'_id':ObjectId(id)})
    if data is None:
        return "User not found", HTTPStatus.NOT_FOUND
    data['_id'] = str(data['_id'])
    print(data)
    return jsonify(data)

# Delete a user from the database
@app.route('/users/<id>/delete', methods=['DELETE'])
def deleteuser(id):
    res = users_col.delete_one({"_id": ObjectId(id)})
    return str(res.deleted_count)

# Add a user to the database
# format for the user in the database:
# user {
#     _id,
#     netid,
#     email,
#     admin,
# }
@app.route('/users/add', methods=['POST'])
def adduser():
    contentType = request.headers.get("Content-Type", "")

    if contentType == "application/json":
        req_keys = {'netid', 'email', 'admin'}
        recv = request.get_json()
        user = {
            'netid': str(recv['netid']),
            'email': str(recv['email']),
            'admin': bool(recv['admin']),
        }

    else:
        recv = request.args.to_dict()
        user = {
            'netid': str(recv['netid']),
            'email': str(recv['email']),
            'admin': bool(recv['admin']),
        }
    
     # try to insert the user into db user collection
    res = users_col.insert_one(user)
    if not ObjectId.is_valid(res.inserted_id):
        return "Insertion failed", HTTPStatus.INTERNAL_SERVER_ERROR

    return str(res.inserted_id), HTTPStatus.CREATED

# @app.route('/users/add/post', methods=['POST'])
# def adduserpost():
#     pass


# ~~~~~~ helper functions ~~~~~~
# These are functions that help in the back-end and cannot be accessed by front-end

# helper function to add machines to database using specified file
def addmachines(fn):
    js = json.load(open(fn))
    for m in js:
        try:
            m['description'] = m['description'].strip().capitalize()
        except Exception as e:
            print(e)
        print(m)
    
    res = machines_col.insert_many(js)
    return json.dumps(res)

# update a machine's name
def updatemachinename(id, name):
    machines_col.update_one({"_id": ObjectId(id)}, {"$set": {"name": name}})

# update a machine description
def updatedescription(id, description):
    machines_col.update_one({"_id": ObjectId(id)}, {"$set": {"description": description}})

# update the image path for a machine
def updateimagepath(id, imagePath):
    machines_col.update_one({"_id": ObjectId(id)}, {"$set": {"image": imagePath}})


if __name__ == "__main__":
    app.run(host='127.0.0.1', debug=True, port=5000)
