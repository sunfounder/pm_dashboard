import time
import logging
import threading

from influxdb import InfluxDBClient

from .database import Database
from .utils import log_error

from sf_rpi_status import \
    get_cpu_temperature, \
    get_gpu_temperature, \
    get_cpu_percent, \
    get_cpu_freq, \
    get_cpu_count, \
    get_memory_info, \
    get_disk_info, \
    get_disks_info, \
    get_boot_time, \
    get_ips, \
    get_macs, \
    get_network_connection_type, \
    get_network_speed

class DataLogger:

    @log_error
    def __init__(self, database='pm_dashboard', interval=1, spc_enabled=False, get_logger=None):
        if get_logger is None:
            get_logger = logging.getLogger
        self.log = get_logger(__name__)

        try:
            self.client = InfluxDBClient(host='localhost', port=8086)
        except Exception as e:
            self.log.error(f"Failed to connect to influxdb: {e}")
            return

        self.spc = None
        self.db = None

        self.thread = None
        self.running = False

        self.db = Database(database, get_logger=get_logger)
        self.interval = interval
        if spc_enabled:
            self.log.info("SPC peripheral enabled")
            from spc.spc import SPC
            self.spc = SPC()
        else:
            self.log.info("SPC peripheral disabled")
        
        self.status = {}

    @log_error
    def set_debug_level(self, level):
        self.log.setLevel(level)

    @log_error
    def update_status(self, status):
        self.status = status

    @log_error
    def set_interval(self, interval):
        self.interval = interval

    @log_error
    def get_data(self):
        boot_time = get_boot_time()
        ips = get_ips()
        macs = get_macs()
        network_connection_type = get_network_connection_type()
        network_speed = get_network_speed()

        data = {}
        data['cpu_temperature'] = float(get_cpu_temperature()) if get_cpu_temperature() is not None else None
        data['gpu_temperature'] = float(get_gpu_temperature()) if get_gpu_temperature() is not None else None
        data['cpu_percent'] = float(get_cpu_percent())
        data['cpu_count'] = int(get_cpu_count())

        cpu_freq = get_cpu_freq()
        data['cpu_freq'] = float(cpu_freq.current)
        data['cpu_freq_min'] = float(cpu_freq.min)
        data['cpu_freq_max'] = float(cpu_freq.max)

        cpu_percents = get_cpu_percent(percpu=True)
        for i, percent in enumerate(cpu_percents):
            data[f'cpu_{i}_percent'] = float(percent)

        memory = get_memory_info()
        data['memory_total'] = int(memory.total)
        data['memory_available'] = int(memory.available)
        data['memory_percent'] = float(memory.percent)
        data['memory_used'] = int(memory.used)

        disks = get_disks_info()
        for disk_name in disks:
            disk = disks[disk_name]
            data[f'disk_{disk_name}_mounted'] = int(disk.mounted)
            data[f'disk_{disk_name}_total'] = int(disk.total)
            data[f'disk_{disk_name}_used'] = int(disk.used)
            data[f'disk_{disk_name}_free'] = int(disk.free)
            data[f'disk_{disk_name}_percent'] = float(disk.percent)

        data['boot_time'] = float(boot_time)

        ips = get_ips()
        for name in ips:
            data[f'ip_{name}'] = ips[name]

        macs = get_macs()
        for name in macs:
            data[f'mac_{name}'] = macs[name]

        data['network_type'] = "&".join(network_connection_type)
        data['network_upload_speed'] = int(network_speed.upload)
        data['network_download_speed'] = int(network_speed.download)

        for name in self.status:
            data[name] = self.status[name]

        if self.spc is not None:
            spc = self.spc.read_all()
            for key in spc:
                data[key] = spc[key]

        for key in data:
            value = data[key]
            if isinstance(value, bool):
                data[key] = int(value)
        return data

    @log_error
    def loop(self):
        start = time.time()
        while self.running:
            data = self.get_data()

            status, msg = self.db.set('history', data)
            if not status:
                self.log.error(f"Failed to set data: {msg}")
            else:
                self.log.debug(f"Set data: {data}")

            elapsed = time.time() - start
            if elapsed < self.interval:
                time.sleep(self.interval - elapsed)
            start += self.interval

    @log_error
    def start(self):
        if self.running:
            self.log.warning("Already running")
            return
        self.db.start()
        self.running = True
        self.thread = threading.Thread(target=self.loop)
        self.thread.start()
        self.log.info("Data Logger Start")

    @log_error
    def stop(self):
        self.log.debug("Stopping Data Logger")
        if self.running:
            self.running = False
            self.thread.join()
            self.db.close()
        self.log.info("Data Logger stopped")
