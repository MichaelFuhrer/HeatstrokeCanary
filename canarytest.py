import requests
import time
import datetime
from flask import Flask, request

TEMP_HOST = 'localhost'
WEBAPP_PORT = '80'


def main():
    # Attain timestamp
    timestamp = time.time()

    # Attain unique ID of canaryPi
    canary_id = str(datetime.datetime.now().strftime('%Y%m%d%H%M%S%f'))

    # Attain temperature todo

    # Prepare HTTP Payload
    payload = {'canary_id': canary_id, 'timestamp': timestamp,
               'temperature': 40}
    image = {'image': open('baby00.jpg', 'rb')}

    url = 'http://' + TEMP_HOST + ':' + WEBAPP_PORT + '/post'
    try:
        r = requests.post(url, data=payload, files=image)
        print("Canary: Event successfully sent to Server")

    except requests.exceptions.ConnectionError as e:
        print(f'Failed to connect to ServerPi: {e}')
        # contact emergency services


if __name__ == "__main__":
    main()
