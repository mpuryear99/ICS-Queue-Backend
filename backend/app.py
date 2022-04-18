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
users_col = db['users']


# ~~~~~~ MACHINE ~~~~~~

# Returns desired machine based on name
@app.route('/machines/<id>', methods=['GET'])
def getmachine(id):
    data = machines_col.find_one({'_id':ObjectId(id)})
    if data != None:
        data['_id'] = str(data['_id'])
        print(data)
        return data

# Returns all the machines in the database
@app.route('/machines', methods=['GET'])
def getmachines():
    data = []
    for m in machines_col.find({}):
        m['_id'] = str(m['_id'])
        data.append(m)
    return json.dumps(data)

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
    print(m)
    res = machines_col.insert_one(m)
    return str(res.inserted_id)

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
        'user_id': ObjectId(recieved['name']),
        'machine_id': ObjectId(recieved['machineID']),
        'username': recieved['username'],
        'startTime': float(recieved['startTime']),
        'endTime': float(recieved['endTime'])
    }
    print("data: ", data)
    
    res = appt_col.insert_one(data)
    return str(res.inserted_id)

# adds an appointment when given json data
@app.route('/appointments/add/post', methods=['POST'])
def addappointmentpost():
    received = request.get_json()
    print(received)

    data = ['user_id','machine_id','username','startTime','endTime']

    for key in received.keys():
        print(key)
        if key == 'user_id':
            user = users_col.find_one({'_id':ObjectId(str(received['user_id']))})
            if user == None:
                return "User does not exist"
        elif key == 'machine_id':
            machine = machines_col.find_one({'_id':ObjectId(str(received['machine_id']))})
            if machine == None:
                return "Machine does not exist"
        elif key == 'username':
            pass
        elif key == 'startTime':
            pass
        elif key == 'endTime':
            pass
        else:
            return "Invalid key"

    res = appt_col.insert_one(received)
    return res

    #res = appt_col.insert_one(received)
    #return str(res.inserted_id)

# Returns all appointments within the week
# example request: GET http://127.0.0.1:5000/getweekappointments/
@app.route('/appointments/week', methods=['GET'])
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
# example request: GET http://127.0.0.1:5000/appointments/
@app.route('/appointments', methods=['GET'])
def getallappointments():
    data = []
    for a in appt_col.find({"_id": {"$gte": 0}}):
        a['_id'] = str(a['_id'])
        data.append(a)
    return json.dumps(data)

# Returns information about an appointment based on its ID
@app.route('/appointments/<id>', methods=['GET'])
def getappointment(id):
    pass

# Deletes an appointment based on its ID
@app.route('/appointments/<id>/delete', methods=['DELETE'])
def deleteappointment(id):
    pass



# ~~~~~~ USERS ~~~~~~

# Returns all the users
@app.route('/users')
def getusers():
    data = []
    for u in users_col.find({}):
        u['_id'] = str(u['_id'])
        data.append(u)
    return json.dumps(data)

# Return a user based on id
@app.route('/users/<id>', methods=['GET'])
def getuser(id):
    pass

# Delete a user from the database
@app.route('/users/<id>/delete', methods=['DELETE'])
def deleteuser(id):
    pass

# Add a user to the database
# format for the user in the database:
# user {
#     _id,
#     netid,
#     email,
#     appointments: [<_id>, ...]
# }
@app.route('/users/add', methods=['POST'])
def adduser():
    recv = request.args.to_dict()

    user = {
        'netid': recv['netid'],
        'email': recv['email'],
        'appointments': []
    }
    print(user)
    res = users_col.insert_one(user)
    return str(res.inserted_id)

# ~~~~~~ helper functions ~~~~~~
# These are functions that help in the back-end and cannot be accessed by front-end

# helper function to add machines to database using specified file
def addmachines(fn):
    js = json.load(open(fn))
    for m in js:
        try:
            if m['description'][0] == ' ':
                m['description']=m['description'][1:]
            m['description'] = m['description'].capitalize()
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
