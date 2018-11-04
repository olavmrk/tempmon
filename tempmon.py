#!/usr/bin/env python3
import influxdb
import math
import os
import queue
import re
import sys
import threading
import time
import traceback

import settings


class Writer:

    def __init__(self):
        self.client = influxdb.InfluxDBClient(**settings.INFLUXDB_CONNECT)
        self.queue = queue.Queue()
        worker = threading.Thread(name='influxdb-writer', target=self.run)
        worker.daemon = True
        worker.start()

    def write_points(self, points):
        self.queue.put(points)

    def _write_points(self, points):
        try:
            self.client.write_points(points)
        except KeyboardInterrupt:
            raise
        except:
            print('Failed to send in temperature data:', file=sys.stderr)
            traceback.print_exc()
            pass

    def run(self):
        while True:
            points = self.queue.get()
            self._write_points(points)


def find_devices():
    devices = set()
    for d in os.listdir('/sys/bus/w1/devices'):
        if d.startswith('28-'): # 0x28 is the device family for thermometer
            devices.add(d)
    return devices

def read_device(device):
    path = os.path.join('/sys/bus/w1/devices', device, 'w1_slave')
    with open(path, 'rt') as fh:
        data = fh.read()
    if not re.search('crc=[0-9a-f]+ YES\n', data):
        print('Invalid measurement from {device}:\n{data}'.format(device=device,data=data), file=sys.stderr)
        raise Exception('Invalid measurement')
    m = re.search('t=(-?\d+)', data)
    milli_temp = int(m.group(1))
    temp =  milli_temp / 1000
    if temp < -55 or temp > 125:
        print('Measurement from {device} out of range:\n{data}'.format(device=device,data=data), file=sys.stderr)
        raise Exception('Measurement out of range')
    return temp

def read_all():
    devices = find_devices()
    ret = {}
    for device in devices:
        try:
            ret[device] = read_device(device)
        except KeyboardInterrupt:
            raise
        except:
            print('Failed to read temperature from {device}:'.format(device=device), file=sys.stderr)
            traceback.print_exc()
            pass
    return ret

    temp_futures = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for device in devices:
            temp_futures[device] = executor.submit(read_device, device)
    ret = {}
    for device in devices:
        temperature = temp_futures[device].result()
        if temperature is not None:
            ret[device] = temperature
    return ret

def do_sample(timestamp, dbclient):
    temperatures = read_all()
    ts_string = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(timestamp))

    json_body = []
    for device, temperature in sorted(temperatures.items()):
        json_body.append({
            'measurement': settings.INFLUXDB_MEASUREMENT,
            'tags': {
                'sensor': device
            },
            'time': ts_string,
            'fields': {
                'value': temperature
            }
        })
    dbclient.write_points(json_body)

def main():
    dbclient = Writer()
    while True:
        current_time = time.time()
        next_time = math.ceil(current_time / 10) * 10
        time.sleep(next_time - current_time)
        do_sample(next_time, dbclient)

if __name__ == '__main__':
    main()
