from flask import Flask, request
from flask_cors import CORS
import os
import routes_db_manager

app = Flask(__name__)
CORS(app)

@app.route('/routes/assign/', methods=['POST'])
def assign_routes():
    params = request.get_json()
    result = routes_db_manager.assign_new_route(params)
    if result:
        return {"result": "Route assigned"}, 201
    else:
        return {"result": "Error assigning a new route"}, 500

@app.route('/routes/retrieve/', methods=['GET'])
def retrieve_routes():
    params = request.get_json()
    result = routes_db_manager.get_routes_assigned_to_vehicle(params)
    return result

if __name__ == '__main__':
    HOST = os.getenv('HOST')
    PORT = os.getenv('PORT')
    app.run(host=HOST, port=PORT)