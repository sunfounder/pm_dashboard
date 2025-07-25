from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError
import json
import logging
import subprocess
import time
from math import floor
import re

from pm_dashboard.utils import log_error
from .config import Config
import threading

INFLUXDB_CONFIG = "/etc/influxdb/influxdb.conf"

class Database:
    def __init__(self, database, log=None, retention_days=30):
        self.log = log or logging.getLogger(__name__)
        self.lock = threading.Lock()

        self.database = database
        self.retention_days = retention_days
        self.influx_manually_started = False

        # disable InfluxDB logging to avoid cluttering the logs
        try:
            config = Config(path=INFLUXDB_CONFIG)
            config.read()
            config['http']['log-enabled'] = 'false'
            config['logging']['level'] = '\"error\"'
            config.write()

            import os
            os.system("systemctl restart influxdb")
            
        except Exception as e:
            self.log.error(f"Failed to disable InfluxDB logging: {e}")

        # initialize InfluxDB client
        self.client = InfluxDBClient(host='localhost', port=8086)
    
    def start(self):
        if not Database.is_influxdb_running():
            self.log.info("Starting influxdb service")
            self.start_influxdb()
            # Wait 2 seconds for InfluxDB to start
            time.sleep(2)

        self.log.debug("Waiting for InfluxDB to be ready")
        for _ in range(10):
            if self.is_ready():
                self.log.info("Influxdb is ready")
                break
            else:
                time.sleep(1)
        else:
            self.log.error("Timeout waiting for InfluxDB to be ready")
            return False

        databases = self.client.get_list_database()
        if not any(db['name'] == self.database for db in databases):
            self.client.create_database(self.database)
            self.log.info(f"Database '{self.database}' created successfully")

        self.client.switch_database(self.database)
        self.ensure_retention_policy_consistency()

    def is_ready(self):
        ports = Database.get_influxdb_ports()
        if len(ports) == 0:
            self.log.error("Influxdb process error, no ports found")
            return False
        if len(ports) == 1:
            self.log.info(f"Influxdb process error, only running on port {ports[0]}")
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
    def get_influxdb_ports():
        command = "lsof -i -P -n | grep LISTEN | grep influxd | awk '{print $9}' | cut -d ':' -f 2"
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, _ = process.communicate()
        output = output.decode('utf-8').strip()
        if output == '':
            return []
        ports = output.split('\n')
        ports = [int(port) for port in ports]
        return ports

    def start_influxdb(self):
        # Start InfluxDB in the background
        subprocess.Popen(["influxd"])
        self.influx_manually_started = True

    def stop_influxdb(self):
        subprocess.Popen(["pkill", "influxd"])

    def parse_influxdb_duration(self, duration_str):
        """解析InfluxDB返回的各种时间格式为天数"""
        if duration_str == "INF":
            return float('inf')
            
        # 处理简单格式：Xd
        if duration_str.endswith('d'):
            try:
                return int(duration_str.rstrip('d'))
            except ValueError:
                pass
                
        # 处理复合格式：支持XhYmZs、XhYm、Xh等任意组合
        match = re.match(r'((\d+)h)?((\d+)m)?((\d+)s)?', duration_str)
        if match:
            hours = int(match.group(2)) if match.group(2) else 0
            minutes = int(match.group(4)) if match.group(4) else 0
            seconds = int(match.group(6)) if match.group(6) else 0
            
            # 转换为天
            total_seconds = hours * 3600 + minutes * 60 + seconds
            return total_seconds / (24 * 3600)
            
        # 无法解析的格式
        self.log.warning(f"Unsupported duration format: {duration_str}")
        return None

    @log_error
    def ensure_retention_policy_consistency(self):
        """确保保留策略与配置一致"""
        try:
            policies = self.client.get_list_retention_policies(self.database)
            default_policy = next((p for p in policies if p["default"]), None)
            
            # 预期的保留时长（天）和InfluxDB格式
            expected_days = self.retention_days
            expected_duration = f"{expected_days}d"
            
            if not default_policy:
                # 创建默认保留策略
                self.set_retention_days(expected_days)
                self.log.info(f"Created default retention policy: {expected_duration}")
            else:
                # 检查现有默认策略是否符合配置
                current_duration = default_policy["duration"]
                
                # 使用增强的解析函数
                current_days = self.parse_influxdb_duration(current_duration)
                
                if current_days is None:
                    self.log.error(f"Failed to parse retention duration: {current_duration}")
                    return
                    
                if current_days != expected_days:
                    # 更新策略
                    self.set_retention_days(expected_days)
                    self.log.info(f"Updated inconsistent retention policy: {current_duration} → {expected_duration}")
                else:
                    self.log.debug(f"Retention policy is consistent: {expected_duration}")

        except Exception as e:
            self.log.exception(f"Failed to check retention policy consistency: {e}")

    @log_error
    def set_retention_days(self, days):
        """设置数据库的默认保留天数"""
        try:
            policy_name = "default_policy"
            duration = f"{days}d"
            
            # 检查策略是否存在
            policies = self.client.get_list_retention_policies(self.database)
            policy_names = [p["name"] for p in policies]
            
            if policy_name in policy_names:
                # 修改现有策略
                self.client.alter_retention_policy(
                    policy_name,
                    database=self.database,
                    duration=duration,
                    replication=1,
                    default=True
                )
                self.log.info(f"Updated retention policy to {duration}")
            else:
                # 创建新策略
                self.client.create_retention_policy(
                    policy_name,
                    duration=duration,
                    replication=1,
                    database=self.database,
                    default=True
                )
                self.log.info(f"Created retention policy {policy_name} with duration {duration}")
                
            return True, f"Retention policy set to {days} days"
            
        except Exception as e:
            self.log.error(f"Failed to set retention policy: {e}")
            return False, str(e)

    def set(self, measurement, data):
        # self.log.debug(f"Setting data to database: measurement={measurement}, data={data}")
        if not self.is_ready():
            self.log.error('Database is not ready')
            return False, 'Database is not ready'
        json_body = [
            {
                "measurement": measurement,
                "fields": data
            }
        ]
        try:
            with self.lock:
                self.client.write_points(json_body)
            return True, json_body
        except InfluxDBClientError as e:
            return False, json.loads(e.content)["error"]
        except Exception as e:
            return False, str(e)

    def get_data_by_time_range(self, measurement, start_time, end_time, keys="*", function="mean", max_size=300):
        # self.log.warning(f"Getting data from database: measurement={measurement}, keys={keys}, start_time={start_time}, end_time={end_time}, function={function}, max_size={max_size}")
        if not self.is_ready():
            self.log.error('Database is not ready')
            return []
        if function not in ["mean", "sum", "min", "max", "count"]:
            self.log.error(f"Invalid function: {function}")
            return []
        if keys != "*":
            newKeys = []
            for k in keys.split(","):
                newKeys.append(f'{function}("{k}") as "{k}"')
            keys = ",".join(newKeys)
        duration = int(end_time) - int(start_time)
        duration_in_seconds = duration / 1000000000
        interval = 1
        if duration_in_seconds > max_size:
            interval = duration_in_seconds / max_size
            interval = floor(interval)
        query = f'SELECT {keys} FROM {measurement} WHERE time >= {start_time} AND time <= {end_time} GROUP BY time({interval}s)'
        # self.log.warning(f"Query: {query}")
        with self.lock:
            result = self.client.query(query)
        return list(result.get_points())

    def if_too_many_nulls(self, result, threshold=0.5):
        for point in result:
            error_length = len([key for key, value in point.items() if value is None])
            error_ratio = error_length / len(point)
            if error_ratio > threshold:
                return True
        return False

    def get(self, measurement, key="*", n=1):
        # self.log.debug(f"Getting data from database: measurement={measurement}, key={key}, n={n}")
        if not self.is_ready():
            self.log.error('Database is not ready')
            return []

        # Read data from last 1 second
        time_filter = "time < now() - 1s"
        query = f"SELECT {key} FROM {measurement} WHERE {time_filter} ORDER BY time DESC LIMIT {n}"
        with self.lock:
            result = self.client.query(query)

        result = list(result.get_points())
        if n == 1:
            if len(result) == 0:
                self.log.debug(f"No data found for query: {query}")
                result = None
            else:
                result = result[0]
                if key != "*" and key != "time" and "," not in key:
                    result = result[key]
        # self.log.debug(f"Got data from database: {result}")
        return result

    def clear_measurement(self, measurement):
        self.log.info(f"Clearing database: {self.database}")
        if not self.is_ready():
            self.log.error('Database is not ready')
            return False
        self.client.drop_measurement(measurement)
        self.log.info(f"Database '{self.database}' cleared successfully")
        return True

    def close(self):
        self.client.close()
        if self.influx_manually_started:
            self.stop_influxdb()
        self.log.info("Database closed")

