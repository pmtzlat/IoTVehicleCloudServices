import os
import json
import datetime
import mysql.connector as mysql


def connect_database():
    mydb = mysql.connector.connect(
        host=os.getenv('DBHOST'),
        user=os.getenv('DBUSER'),
        password=os.getenv('DBPASSWORD'),
        database=os.getenv('DBDATABASE')
    )
    return mydb

def get_routes_assigned_to_vehicle(params):
    result = []
    try:
        mydb = connect_database()
        with mydb.cursor() as cursor:
            sql = """SELECT origin, destination, plate, time_stamp 
                FROM routes 
                WHERE plate = %s 
                ORDER BY time_stamp DESC"""
            vehicle_plate = params["vehicle_plate"]
            query_params = (vehicle_plate,)
            cursor.execute(sql, query_params)
            my_result = cursor.fetchall()
            for origin, destination, plate, time_stamp in my_result:
                item = {"Origin": origin, "Destination": destination, "Plate": plate,
                        "Time Stamp": time_stamp}
                result.append(item)
        return result
    except Exception as e:
        print("Error getting the routes assigned to this plate: ", vehicle_plate)
        return None


def assign_new_route(params):
    result = True
    try:
        mydb = connect_database()
        with mydb.cursor() as cursor:
            sql = """INSERT INTO vehicles_telemetry (origin, destination, plate, time_stamp) 
                VALUES( % s, %s, %s, %s)"""
        vehicle_plate = params["vehicle_plate"]
        origin = params["origin"]
        destination = params["destination"]
        time_stamp = datetime.datetime.now()
        tuples = (vehicle_plate, origin, destination, time_stamp)
        cursor.execute(sql, tuples)
        mydb.commit()
        print(cursor.rowcount, "Route inserted.")
        return result
    except Exception as e:
        print("ERROR on route insertion!" + str(e))
        print(params)
        result = False
        return result
