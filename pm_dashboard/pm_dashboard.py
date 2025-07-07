
import threading
import logging
from os import listdir, path, remove

import flask
from flask import request, send_from_directory
from flask_cors import CORS, cross_origin
from importlib.resources import files as resource_files
from werkzeug.serving import make_server

from .data_logger import DataLogger
from .database import Database
from .utils import log_error, merge_dict
import logging
from sf_rpi_status import get_disks, get_ips

DEBUG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

__package_name__ = __name__.split('.')[0]
__log_path__ = '/var/log/pironman5'
__www_path__ = str(resource_files(__package_name__).joinpath('www'))
__api_prefix__ = '/api/v1.0'
__host__ = '0.0.0.0'
__port__ = 34001
__log__ = None

__db__ = None
__data_logger__ = None
__config__ = {}
__app__ = flask.Flask(__name__, static_folder=__www_path__)

__app__.logger.setLevel(logging.WARN)
logging.getLogger('werkzeug').setLevel(logging.ERROR)


__cors__ = CORS(__app__)
__app__.config['CORS_HEADERS'] = 'Content-Type'
__device_info__ = {}
__mqtt_connected__ = False
__enable_history__ = False

__on_outside_config_changed__ = lambda config: None
__on_inside_config_changed__ = lambda config: None

def __on_config_changed__(config):
    global __config__, __on_outside_config_changed__, __on_inside_config_changed__
    __on_outside_config_changed__(config)
    __on_inside_config_changed__(config)
    __config__ = merge_dict(__config__, config)

def on_mqtt_connected(client, userdata, flags, rc):
    global __mqtt_connected__
    if rc==0:
        __mqtt_connected__ = True
    else:
        __mqtt_connected__ = False

def _get_log(name, line_count=100, filter=[], level="INFO"):
    if path.exists(f"{__log_path__}/{name}") == False:
        return False
    with open(f"{__log_path__}/{name}", 'r') as f:
        lines = f.readlines()
        lines = lines[-line_count:]
        data = []
        for line in lines:
            check = True
            if len(filter) > 0:
                for f in filter:
                    if f in line:
                        break
                else:
                    check = False
            log_level = DEBUG_LEVELS.index(level)
            current_log_level = DEBUG_LEVELS.index(get_log_level(line))
            if current_log_level < log_level:
                check = False
            if check:
                data.append(line)
        return data

def _test_mqtt(config, timeout=5):
    global __mqtt_connected__
    import paho.mqtt.client as mqtt
    from socket import gaierror
    import time
    __mqtt_connected__ = None
    client = mqtt.Client()
    client.on_connect = on_mqtt_connected
    client.username_pw_set(config['username'], config['password'])
    try:
        client.connect(config['host'], config['port'])
    except gaierror:
        return False, "Connection failed, Check hostname and port"
    timestart = time.time()
    while time.time() - timestart < timeout:
        client.loop()
        if __mqtt_connected__ == True:
            return True, None
        elif __mqtt_connected__ == False:
            return False, "Connection failed, Check username and password"
    return False, "Timeout"

def get_log_level(line):
    for level in DEBUG_LEVELS:
        if f"[{level}]" in line:
            return level
    return 'INFO'

# Host dashboard page
@__app__.route('/')
@cross_origin()
def dashboard():
    with open(f'{__app__.static_folder}/index.html') as f:
        return f.read()

# Host static files for dashboard page
@__app__.route('/<path:filename>')
@cross_origin()
def serve_static(filename):
    path = __app__.static_folder
    if '/' in filename:
        items = filename.split('/')
        filename = items[-1]
        path = path + '/' + '/'.join(items[:-1])
    return send_from_directory(path, filename)

# host API
@__app__.route(f'{__api_prefix__}/get-version')
@cross_origin()
def get_version():
    return {"status": True, "data": __device_info__['version']}

@__app__.route(f'{__api_prefix__}/get-device-info')
@cross_origin()
def get_device_info():
    return {"status": True, "data": __device_info__}

@__app__.route(f'{__api_prefix__}/test')
@cross_origin()
def test():
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/test-mqtt')
@cross_origin()
def test_mqtt():
    host = request.args.get("host")
    port = request.args.get("port")
    username = request.args.get("username")
    password = request.args.get("password")
    mqtt_config = {}
    data = None
    status = True
    error = None
    if host is None:
        status = False
        error = "[ERROR] host not found"
    elif port is None:
        status = False
        error = "[ERROR] port not found"
    elif username is None:
        status = False
        error = "[ERROR] username not found"
    elif password is None:
        status = False
        error = "[ERROR] password not found"
    else:
        mqtt_config['host'] = host
        mqtt_config['port'] = int(host)
        mqtt_config['username'] = username
        mqtt_config['password'] = password
        result = _test_mqtt(mqtt_config)
        data = {
            "status": result[0],
            "error": result[1]
        }
        status = True
    result = {"status": status}
    if status:
        result['data'] = data
    else:
        result['error'] = error
    return result

@__app__.route(f'{__api_prefix__}/get-data')
@cross_origin()
def get_data():
    try:
        if __enable_history__ == False:
            data = __data_logger__.get_data()
        else:
            num = request.args.get("n")
            if num is None:
                num = 1
            else:
                num = int(num)
            data = __db__.get("history", n=num)
        return {"status": True, "data": data}
    except Exception as e:
        return {"status": False, "error": str(e)}

@__app__.route(f'{__api_prefix__}/get-history')
@cross_origin()
def get_history():
    try:
        if __enable_history__ == False:
            data = __data_logger__.get_data()
        else:
            num = request.args.get("n")
            if num is None:
                num = 1
            else:
                num = int(num)
            data = __db__.get("history", n=num)
        return {"status": True, "data": data}
    except Exception as e:
        return {"status": False, "error": str(e)}

@__app__.route(f'{__api_prefix__}/get-time-range')
@cross_origin()
def get_time_range():
    try:
        if __enable_history__:
            start = request.args.get("start")
            end = request.args.get("end")
            key = request.args.get("key")
            data = __db__.get_data_by_time_range("history", start, end, key)
            return {"status": True, "data": data}
        else:
            return {"status": False, "error": "History is not enabled"}
    except Exception as e:
        return {"status": False, "error": str(e)}

@__app__.route(f'{__api_prefix__}/get-config')
@cross_origin()
def get_config():
    return {"status": True, "data": __config__}

@__app__.route(f'{__api_prefix__}/get-log-list')
@cross_origin()
def get_log_list():
    log_files = listdir(__log_path__)
    return {"status": True, "data": log_files}

@__app__.route(f'{__api_prefix__}/get-log')
@cross_origin()
def get_log():
    filename = request.args.get("filename")
    filter = request.args.get("filter")
    level = request.args.get("level")
    lines = request.args.get("lines")
    if filename is None:
        return {"status": False, "error": "[ERROR] file not found"}
    if lines is None:
        lines = 100
    else:
        lines = int(lines)
    if filter is not None:
        filter = filter.split(',')
    else:
        filter = []
    if level is None:
        level = "INFO"
    else:
        if level not in DEBUG_LEVELS:
            return {"status": False, "error": f"[ERROR] level {level} not found"}
    content = _get_log(filename, lines, filter, level)
    if content is False:
        return {"status": False, "error": f"[ERROR] file {filename} not found"}
    return {"status": True, "data": content}

@__app__.route(f'{__api_prefix__}/get-default-on')
@cross_origin()
def get_default_on():
    default_on = __db__.get("history", "default_on")
    return {"status": True, "data": default_on}

@__app__.route(f'{__api_prefix__}/get-disk-list')
@cross_origin()
def get_disk_list():
    return {"status": True, "data": get_disks()}

@__app__.route(f'{__api_prefix__}/get-network-interface-list')
@cross_origin()
def get_network_interface_list():
    interfaces = list(get_ips().keys())
    return {"status": True, "data": interfaces}

@__app__.route(f'{__api_prefix__}/set-temperature-unit', methods=['POST'])
@cross_origin()
def set_temperature_unit():
    unit = request.json["unit"]
    unit = unit.upper()
    if unit not in ['C', 'F']:
        return {"status": False, "error": f"[ERROR] temperature unit {unit} not found, available units: C, F"}
    __on_config_changed__({'system': {'temperature_unit': unit}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/set-shutdown-percentage', methods=['POST'])
@cross_origin()
def set_shutdown_percentage():
    percentage = request.json["shutdown-percentage"]
    __on_config_changed__({'system': {'shutdown_percentage': percentage}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/set-fan-led', methods=['POST'])
@cross_origin()
def set_fan_led():
    led = request.json["led"]
    if led not in ['on', 'off', 'follow']:
        return {"status": False, "error": f"[ERROR] led {led} not found, available values: on, off or follow"}
    __on_config_changed__({'system': {'gpio_fan_led': led}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/set-fan-mode', methods=['POST'])
@cross_origin()
def set_fan_mode():
    mode = request.json["fan_mode"]
    if not isinstance(mode, int):
        return {"status": False, "error": f"[ERROR] fan mode {mode} not found, available modes: 0, 1, 2, 3, 4, for Alway On, Performance, Cool, Balance, or Silent"}
    if mode < 0 or mode > 4:
        return {"status": False, "error": f"[ERROR] fan mode {mode} not found, available modes: 0, 1, 2, 3, 4, for Alway On, Performance, Cool, Balance, or Silent"}
    __on_config_changed__({'system': {'gpio_fan_mode': mode}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/set-rgb-brightness', methods=['POST'])
@cross_origin()
def set_rgb_brightness():
    brightness = request.json["brightness"]
    __on_config_changed__({'system': {'rgb_brightness': brightness}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/set-rgb-color', methods=['POST'])
@cross_origin()
def set_rgb_color():
    color = request.json["color"]
    __on_config_changed__({'system': {'rgb_color': color}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/set-rgb-enable', methods=['POST'])
@cross_origin()
def set_rgb_enable():
    enable = request.json["enable"]
    __on_config_changed__({'system': {'rgb_enable': enable}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/set-rgb-led-count', methods=['POST'])
@cross_origin()
def set_rgb_led_count():
    led_count = request.json["led-count"]
    __on_config_changed__({'system': {'rgb_led_count': led_count}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/set-rgb-style', methods=['POST'])
@cross_origin()
def set_rgb_style():
    style = request.json["style"]
    __on_config_changed__({'system': {'rgb_style': style}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/set-rgb-speed', methods=['POST'])
@cross_origin()
def set_rgb_speed():
    speed = request.json["speed"]
    __on_config_changed__({'system': {'rgb_speed': speed}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/set-oled-sleep-timeout', methods=['POST'])
@cross_origin()
def set_oled_sleep_timeout():
    timeout = request.json["timeout"]
    if not isinstance(timeout, (int, float)) or timeout < 0:
        return {"status": False, "error": f"[ERROR] timeout {timeout} must be a positive number"}
    __on_config_changed__({'system': {'oled_sleep_timeout': timeout}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/set-oled-enable', methods=['POST'])
@cross_origin()
def set_oled_enable():
    enable = request.json["enable"]
    if not isinstance(enable, bool):
        return {"status": False, "error": f"[ERROR] enable {enable} not found, available values: True or False"}
    __on_config_changed__({'system': {'oled_enable': enable}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/set-oled-disk', methods=['POST'])
@cross_origin()
def set_oled_disk():
    disk = request.json["disk"]
    disks = ["total"]
    disks.extend(get_disks())

    if disk is None:
        disk = "total"
    elif disk not in disks:
        return {"status": False, "error": f"[ERROR] disk {disk} not found, available disks: {disks}"}
    __on_config_changed__({'system': {'oled_disk': disk}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/set-oled-network-interface', methods=['POST'])
@cross_origin()
def set_oled_network_interface():
    interface = request.json["interface"]
    interfaces = ['all']
    interfaces.extend(get_ips().keys())

    if interface is None:
        interface = "eth0"
    elif interface not in interfaces:
        return {"status": False, "error": f"[ERROR] interface {interface} not found, available interfaces: {interfaces}"}
    __on_config_changed__({'system': {'oled_network_interface': interface}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/set-oled-rotation', methods=['POST'])
@cross_origin()
def set_oled_rotation():
    rotation = request.json["rotation"]
    if rotation not in [0, 180]:
        return {"status": False, "error": f"[ERROR] rotation {rotation} not found, available values: 0 or 180"}
    __on_config_changed__({'system': {'oled_rotation': rotation}})
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/clear-history', methods=['POST', 'GET'])
@cross_origin()
def clear_history():
    if __enable_history__ == False:
        return {"status": False, "error": "History is not enabled"}
    __db__.clear_measurement('history')
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/delete-log-file', methods=['POST'])
@cross_origin()
def delete_log_file():
    filename = request.json["filename"]
    if filename is None:
        return {"status": False, "error": "[ERROR] file not found"}
    if path.exists(f"{__log_path__}/{filename}") == False:
        return {"status": False, "error": f"[ERROR] file {filename} not found"}
    try:
        remove(f"{__log_path__}/{filename}")
        return {"status": True, "data": "OK"}
    except Exception as e:
        return {"status": False, "error": str(e)}

@__app__.route(f'{__api_prefix__}/start-ups-power-failure-simulation', methods=['POST', 'GET'])
@cross_origin()
def set_ups_vbus_enable():
    import subprocess
    time = request.json["time"]
    print(f"start-ups-blackout-simulation {time}")
    subprocess.Popen(['sudo', 'pipower5', '--power-failure-simulation', f'{time}'])
    return {"status": True, "data": "OK"}

@__app__.route(f'{__api_prefix__}/get-ups-power-failure-simulation', methods=['POST', 'GET'])
@cross_origin()
def get_ups_blackout_simulation():
    import json
    with open('/opt/pipower5/blackout_simulation.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {"status": True, "data":data}


class PMDashboard():
    def __init__(self, device_info=None, database='pm_dashboard', spc_enabled=False, config=None, log=None):
        global __config__, __device_info__, __on_inside_config_changed__, __log_path__, __enable_history__
        global __data_logger__, __db__, __log__
        __device_info__ = device_info
        if 'app_name' in __device_info__:
            app_name = __device_info__['app_name']
        else:
            app_name = __device_info__['id']
        __log_path__ = f'/var/log/{app_name}'

        self.log = log or logging.getLogger(__name__)
        __log__ = self.log

        __config__ = config
        if 'enable_history' not in __config__['system']:
            __config__['system']['enable_history'] = False
        __enable_history__ = config['system']['enable_history']

        self.data_logger = DataLogger(
            database=database,
            spc_enabled=spc_enabled,
            interval=__config__['system']['data_interval'],
            log=log)
        __data_logger__ = self.data_logger
        if __enable_history__:
            __db__ = Database(database, log=log)

        self.started = False
        __on_inside_config_changed__ = self.on_config_changed

    @log_error
    def update_status(self, status):
        self.data_logger.update_status(status)

    @log_error
    def start(self):
        if __db__:
            __db__.start()
        self.server = make_server(__host__, __port__, __app__)
        self.ctx = __app__.app_context()
        self.ctx.push()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    @log_error
    def on_config_changed(self, config):
        if 'data_interval' in config['system']:
            self.data_logger.set_interval(config['system']['data_interval'])
        if 'enable_history' in config['system']:
            if config['system']['enable_history'] == True:
                if __enable_history__ == False:
                    self.data_logger.start()
                __enable_history__ = True
            else:
                if __enable_history__ == True:
                    self.data_logger.stop()
                __enable_history__ = False


    @log_error
    def set_on_config_changed(self, func):
        global __on_outside_config_changed__
        __on_outside_config_changed__ = func

    @log_error
    def run(self):
        self.log.info("Dashboard Server start")
        self.started = True
        if __enable_history__:
            self.data_logger.start()
        self.server.serve_forever()

    @log_error
    def shutdown(self):
        self.server.shutdown()

    @log_error
    def stop(self):
        self.log.debug("Stopping Dashboard Server")
        if self.started:
            self.data_logger.stop()
            if __db__:
                __db__.close()
            self.server.shutdown()
            self.server.server_close()
            self.started = False
            self.thread.join(timeout=5)
            self.log.info("Dashboard Server stopped")

