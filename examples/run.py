from pm_dashboard.pm_dashboard import PMDashboard
import time

config = {
    "database": "pm_dashboard",
    "interval": 1,
    "spc": False,
}

server = PMDashboard(config)
server.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("KeyboardInterrupt")
finally:
    server.stop()
