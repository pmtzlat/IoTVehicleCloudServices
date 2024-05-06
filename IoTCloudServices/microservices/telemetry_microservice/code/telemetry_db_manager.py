
import os
import json
from datetime import datetime

import mysql.connector as mysql


def connect_database():
    mydb = mysql.connect(
        host=os.getenv('DBHOST'),
        user=os.getenv('DBUSER'),
        password=os.getenv('DBPASSWORD'),
        database=os.getenv('DBDATABASE')
    )
    return mydb

def register_new_telemetry(params, app):
    result = True
    try:
        mydb = connect_database()
        with mydb.cursor() as cursor:
            sql = """
                INSERT INTO vehicles_telemetry (
                    vehicle_id, current_steering, current_speed, 
                    latitude, longitude, current_ldr, 
                    current_obstacle_distance, front_left_led_intensity, 
                    front_right_led_intensity, rear_left_led_intensity, 
                    rear_right_led_intensity, front_left_led_color, 
                    front_right_led_color, rear_left_led_color, 
                    rear_right_led_color, front_left_led_blinking, 
                    front_right_led_blinking, rear_left_led_blinking, 
                    rear_right_led_blinking, time_stamp
                ) VALUES (
                    %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s, %s
                )
            """

            telemetry = params["telemetry"]
            #values
            vehicle_id = params["vehicle_id"]
            app.logger.info('Telemetry: ', telemetry)
            current_steering = telemetry["current_steering"]
            current_speed = telemetry["current_speed"]
            current_position = json.loads(telemetry["current_position"])
            app.logger.info(current_position)
            latitude = current_position["latitude"]
            longitude = current_position["longitude"]
            current_ldr = telemetry["current_ldr"]
            current_obstacle_distance = telemetry["current_obstacle_distance"]
            time_str = telemetry["time_stamp"]
            format_str = "%Y-%m-%dT%H:%M:%S.%f"
            datetime_obj = datetime.strptime(time_str, format_str)
            time_stamp = datetime_obj
            current_leds = json.loads(telemetry["current_leds"])
            app.logger.debug(current_leds)
            app.logger.debug(f'Loading led data...{current_leds}')
            #Sacar la info individual de las leds
            for led in current_leds:
                if led["Light"] == "Front" and led["Orientation"] == "Right":
                    front_right_led_intensity = led["Intensity"]
                    front_right_led_color = led["Color"]
                    front_right_led_blinking = led["Blinking"]
                if led["Light"] == "Front" and led["Orientation"] == "Left":
                    front_left_led_intensity = led["Intensity"]
                    front_left_led_color = led["Color"]
                    front_left_led_blinking = led["Blinking"]
                if led["Light"] == "Back" and led["Orientation"] == "Right":
                    rear_right_led_intensity = led["Intensity"]
                    rear_right_led_color = led["Color"]
                    rear_right_led_blinking = led["Blinking"]
                if led["Light"] == "Back" and led["Orientation"] == "Left":
                    rear_left_led_intensity = led["Intensity"]
                    rear_left_led_color = led["Color"]
                    rear_left_led_blinking = led["Blinking"]

            val = (vehicle_id, current_steering, current_speed,
                    latitude, longitude, current_ldr,
                    current_obstacle_distance, front_left_led_intensity,
                    front_right_led_intensity, rear_left_led_intensity,
                    rear_right_led_intensity, front_left_led_color,
                    front_right_led_color, rear_left_led_color,
                    rear_right_led_color, front_left_led_blinking,
                    front_right_led_blinking, rear_left_led_blinking,
                    rear_right_led_blinking, time_stamp)
            app.logger.debug("Inserting: " + str(val))
            cursor.execute(sql, val)
            mydb.commit()
            app.logger.debug("Success!")
    except Exception as e:
        app.logger.debug("ERROR on telemetry insertion!" + str(e))
        #app.logger.debug(params)
        raise
        result = False
    return result

def get_vehicle_detailed_info(params, app):
    result = {"Error Message": None, "data": []}
    try:
        mydb = connect_database()
        sql = """SELECT vehicle_id, current_steering, current_speed, current_ldr,
            current_obstacle_distance, front_left_led_intensity,
            front_right_led_intensity, rear_left_led_intensity,
            rear_right_led_intensity, front_left_led_color,
            front_right_led_color, rear_left_led_color, rear_right_led_color,
            front_left_led_blinking, front_right_led_blinking,
            rear_left_led_blinking, rear_right_led_blinking, time_stamp 
            FROM vehicles_telemetry 
            WHERE vehicle_id = %s 
            ORDER BY time_stamp DESC LIMIT 20"""
        vehicle_id = params["vehicle_id"]
        query_params = (vehicle_id,)
        app.logger.debug('Getting detailed info for vehicle {}'.format(vehicle_id))
        with mydb.cursor() as cursor:
            cursor.execute(sql, query_params)
            my_result = cursor.fetchall()
            for (vehicle_id, current_steering, current_speed, current_ldr,
                current_obstacle_distance, front_left_led_intensity,
                front_right_led_intensity, rear_left_led_intensity,
                rear_right_led_intensity, front_left_led_color,
                front_right_led_color, rear_left_led_color,
                rear_right_led_color, front_left_led_blinking,
                front_right_led_blinking, rear_left_led_blinking,
                rear_right_led_blinking, time_stamp) in my_result:
                item = {
                    "Vehicle_id": vehicle_id,
                    "Current Steering": current_steering,
                    "Current Speed": current_speed,
                    "Current LDR": current_ldr,
                    "Obstacle Distance": current_obstacle_distance,
                    "Front Left Led Intensity": front_left_led_intensity,
                    "Front Right Led Intensity": front_right_led_intensity,
                    "Rear Left Led Intensity": rear_left_led_intensity,
                    "Rear Right Led Intensity": rear_right_led_intensity,
                    "Front Left Led Color": front_left_led_color,
                    "Front Right Led Color": front_right_led_color,
                    "Rear Left Led Color": rear_left_led_color,
                    "Rear Right Led Color": rear_right_led_color,
                    "Front Left Led Blinking": front_left_led_blinking,
                    "Front Right Led Blinking": front_right_led_blinking,
                    "Rear Left Led Blinking": rear_left_led_blinking,
                    "Rear Right Led Blinking": rear_right_led_blinking,
                    "Time Stamp": str(time_stamp.isoformat())
                }
                result["data"].append(item)

    except Exception as e:
        app.logger.debug('Error getting detailed infor for car: {} : {}' .format(params['vehicle_id'], e))
        result["Error Message"] = str(e)

    return result


def get_vehicles_last_position(app):
    result = {"Error Message": None, "data": []}
    try:
        mydb = connect_database()
        sql = """SELECT v.vehicle_id, v.plate, vt.latitude, vt.longitude, vt.time_stamp
                FROM vehicles v
                JOIN (
                    SELECT vehicle_id, MAX(time_stamp) AS max_time
                    FROM vehicles_telemetry
                    GROUP BY vehicle_id
                ) AS latest_telemetry
                ON v.vehicle_id = latest_telemetry.vehicle_id
                JOIN vehicles_telemetry vt
                ON vt.vehicle_id = v.vehicle_id AND vt.time_stamp = latest_telemetry.max_time;"""
        with mydb.cursor() as cursor:
            app.logger.debug('Getting vehicles last position...')
            cursor.execute(sql)
            my_result = cursor.fetchall()
            app.logger.debug('Success!')
            for vehicle_id, plate, latitude, longitude, time_stamp in my_result:
                item = {"vehicle_id": vehicle_id, "plate": plate, "Latitude":
                    latitude, "Longitude": longitude, "time_stamp": str(time_stamp.isoformat())}
                result["data"].append(item)
    except Exception as e:
        app.logger.debug(f'Error getting vehicles\' last position: {e}')
        result["Error Message"] = str(e)

    return result
