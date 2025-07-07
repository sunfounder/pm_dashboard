import logging
from pm_dashboard.pm_dashboard import PMDashboard

get_child_logger = logging.getLogger

config = {
    "system": {
        "rgb_color": "#0a1aff",
        "rgb_brightness": 50,
        "rgb_style": "breathing",
        "rgb_speed": 50,
        "rgb_enable": True,
        "rgb_led_count": 4,
        "temperature_unit": "C",
        "oled_enable": True,
        "oled_rotation": 0,
        "oled_disk": "total",
        "oled_network_interface": "all",
        "gpio_fan_pin": 6,
        "gpio_fan_mode": 2,
        "gpio_fan_led": "follow",
        "gpio_fan_led_pin": 5,
    }
}

PERIPHERALS = [
    'storage',
    "cpu",
    "network",
    "memory",
    "history",
    "log",
    "ws2812",
    "temperature_unit",
    "oled",
    "clear_history",
    "delete_log_file",
    "pwm_fan_speed",
    "gpio_fan_state",
    "gpio_fan_mode",
    "gpio_fan_led",
]

DEVICE_INFO = {
    'name': 'Pironman 5',
    'id': 'pironman5',
    'peripherals': PERIPHERALS,
    'version': "0.0.1",
}

DASHBOARD_SETTINGS = {
    "database": "pironman5",
    "data_interval": 1,
    "spc": False,
}

pm_dashboard = PMDashboard(device_info=DEVICE_INFO,
                            settings=DASHBOARD_SETTINGS,
                            config=config,
                            peripherals=PERIPHERALS,
                            log=log)

pm_dashboard.set_debug_level(logging.DEBUG)
pm_dashboard.start()
