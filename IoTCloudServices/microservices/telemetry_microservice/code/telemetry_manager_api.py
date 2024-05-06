import json

from flask import Flask, request
from flask_cors import CORS
import os
import telemetry_db_manager
import logging

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
CORS(app)

@app.route('/telemetry/register/', methods=['POST'])
def register_telemetry():

    app.logger.debug('API - executing register_telemetry')
    vehicle_data = request.get_json()
    result = telemetry_db_manager.register_new_telemetry(vehicle_data, app)
    if result:
        return {"result": "Telemetry registered"}, 201
    else:
        return {"result": "Error registering telemetries"}, 500

@app.route('/telemetry/vehicle/detailed_info/', methods=['GET'])
def telemetry_vehicle_detailedinfo():
    app.logger.debug('API - executing telemetry_vehicle_detailedinfo')
    vehicle_data = request.get_json()
    result = telemetry_db_manager.get_vehicle_detailed_info(vehicle_data, app)
    if result["Error Message"] is None:
        return json.dumps(result), 201
    else:
        return result, 500

@app.route('/telemetry/vehicle/positions/', methods=['GET'])
def telemetry_vehicle_positions():
    app.logger.debug('API - executing telemetry_vehicle_positions')
    result = telemetry_db_manager.get_vehicles_last_position(app)

    if result["Error Message"] is None:
        return json.dumps(result), 201
    else:
        return result, 500


if __name__ == '__main__':
    HOST = os.getenv('HOST')
    PORT = os.getenv('PORT')
    app.run(host=HOST, port=PORT)
