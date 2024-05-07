from flask import Flask, request
from flask_cors import CORS
import os
import routes_db_manager
import logging

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
CORS(app)

@app.route('/routes/complete/', methods=['POST'])
def complete_routes():
    params = request.get_json()
    app.logger.debug(params)
    result = routes_db_manager.complete_route(params, app)
    if result:
        app.logger.debug('Route successfully completed')
        return {"result": "Success"}, 201
    else:
        app.logger.debug('Route could not be completed')
        return {"result": "Failure"}, 500


@app.route('/routes/assign/', methods=['POST'])
def assign_routes():
    params = request.get_json()
    app.logger.debug(params)

    result = routes_db_manager.assign_new_route(params, app)
    if result == 1:
        app.logger.debug('Route assignment successful')
        return {"result": "Route assigned"}, 201

    if result == 0:
        app.logger.debug('Plate is already assigned a route, or plate is not assigned a vehicle')
        return {"result": "Vehicle busy or plate is not assigned a vehicle"}, 202

    else:
        app.logger.debug('Route assignment NOT successful')
        return {"result": "Error assigning a new route"}, 500

@app.route('/routes/retrieve/', methods=['GET'])
def retrieve_routes():
    params = request.get_json()
    app.logger.debug(params)
    result = routes_db_manager.get_routes_assigned_to_vehicle(params, app)
    app.logger.debug('Result: '+ result)
    return result

if __name__ == '__main__':
    HOST = os.getenv('HOST')
    PORT = os.getenv('PORT')
    app.run(host=HOST, port=PORT)