
def get_pwm_fan_speed():
    import os
    '''
    path =  '/sys/devices/platform/cooling_fan/hwmon/*/fan1_input'
    '''
    dir = '/sys/devices/platform/cooling_fan/hwmon/'
    secondary_dir = os.listdir(dir)
    path = f'{dir}/{secondary_dir[0]}/fan1_input'

    with open(path, 'r') as f:
        speed = int(f.read())
    return speed