from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError
import json
import logging
import subprocess
import time

class Database:
    def __init__(self, database, get_logger=None):
        if get_logger is None:
            get_logger = logging.getLogger
        self.log = get_logger(__name__)
        self.database = database

        self.client = InfluxDBClient(host='localhost', port=8086)
    
    def start(self):
        if not Database.is_influxdb_running():
            self.log.info("Starting influxdb service")
            Database.start_influxdb()
            # Wait 2 seconds for InfluxDB to start
            time.sleep(2)

        for _ in range(3):
            self.log.debug("Checking if influxdb is ready...")
            if self.is_ready():
                self.log.info("Influxdb is ready")
                break
            else:
                time.sleep(1)
                self.log.warning("Influxdb is not ready, trying again...")
        else:
            self.log.error("Influxdb is not ready after 3 attempts")

        databases = self.client.get_list_database()
        if not any(db['name'] == self.database for db in databases):
            self.client.create_database(self.database)
            self.log.info(f"Database '{self.database}' not exit, created successfully")

        self.client.switch_database(self.database)

    def is_ready(self):
        try:
            return self.client.ping()
        except Exception as e:
            return False

    @staticmethod
    def is_influxdb_running():
        try:
            # Use 'pgrep' to find the process
            subprocess.check_output(["pgrep", "influxd"])
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def start_influxdb():
        # Start InfluxDB in the background
        subprocess.Popen(["influxd"])

    @staticmethod
    def stop_influxdb():
        # Stop InfluxDB
        subprocess.Popen(["pkill", "influxd"])

    def set(self, measurement, data):
        if not self.is_ready():
            self.log.error('Database is not ready')
            return []
        json_body = [
            {
                "measurement": measurement,
                "fields": data
            }
        ]
        try:
            self.client.write_points(json_body)
            return True, json_body
        except InfluxDBClientError as e:
            return False, json.loads(e.content)["error"]
        except Exception as e:
            return False, str(e)

    def get_data_by_time_range(self, measurement, start_time, end_time, key="*"):
        if not self.is_ready():
            self.log.error('Database is not ready')
            return []
        query = f"SELECT {key} FROM {measurement} WHERE time >= {start_time} AND time <= {end_time}"
        result = self.client.query(query)
        return list(result.get_points())

    def if_too_many_nulls(self, result, threshold=0.3):
        for point in result:
            error_length = len([key for key, value in point.items() if value is None])
            error_ratio = error_length / len(point)
            if error_ratio > threshold:
                return True
        return False

    def get(self, measurement, key="*", n=1):
        if not self.is_ready():
            self.log.error('Database is not ready')
            return []
        for _ in range(3):
            query = f"SELECT {key} FROM {measurement} ORDER BY time DESC LIMIT {n}"
            result = self.client.query(query)
            if self.if_too_many_nulls(list(result.get_points())):
                self.log.warning(f"Too many nulls in the result of query: {query}, result: {list(result.get_points())}. trying again...")
                continue
            break
        else:
            return None
        if n == 1:
            if len(list(result.get_points())) == 0:
                return None
            if key != "*" and key != "time" and "," not in key:
                return list(result.get_points())[0][key]
            return list(result.get_points())[0]
        
        return list(result.get_points())

    def close(self):
        self.client.close()
        Database.stop_influxdb()

