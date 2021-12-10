from motion_monitor import motion_monitor
import time
from picamera import PiCamera
import requests
from datetime import datetime  # For console print timestamps
import keys
from lib.rekognition.rekognition_image_detection import RekognitionImage
import boto3
import json
from twilio.rest import Client
import temp_reader

# Rekognition client and alert labels
rekognition_client = boto3.client('rekognition',
                                  aws_access_key_id=keys.aws_access_id,
                                  aws_secret_access_key=keys.aws_secret_id,
                                  region_name='us-east-1')

baby_alert_labels = ['Baby', 'Person']
pet_alert_labels = ['Dog', 'Pet']

min_temp_alert = 60
min_temp_emergency = 80

mm = motion_monitor()
camera = PiCamera()
canary_id = keys.canary_id


def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")


def send_emergency_sms():
    client = Client(keys.twilio_sid, keys.twilio_auth)
    message = f"EMERGENCY CONTACT MESSAGE. DEVICE ID {keys.canary_id}"
    client.messages.create(body=message, from_=keys.twilio_phone, to=keys.emergency_contact)


def parked_event():
    print(f"[{get_timestamp()}] Car is parked.")


def moving_event():
    print(f"[{get_timestamp()}] Car is moving.")


def take_photo():
    # Take photograph
    img_timestamp = time.time()
    image_file = f'./captures/capture-{img_timestamp}.jpg'
    camera.capture(image_file)
    return image_file


def check_photo(image_filename):
    # Use photograph to determine whether there is a baby or dog in photo
    rekognition = RekognitionImage.from_file(image_filename, rekognition_client)
    labels = rekognition.detect_labels(20)
    confidence_dict = {label.name: label.confidence for label in labels}

    relevant_labels = []
    for label in confidence_dict:
        if (label in baby_alert_labels) or (label in pet_alert_labels):
            relevant_labels.append([label, confidence_dict[label]])

    if len(relevant_labels) > 0:
        print(f'[{get_timestamp()}] Relevant labels found in photo:')
        for entry in relevant_labels:
            print(f'\t{entry}')
    else:
        print(f'[{get_timestamp()}] No relevant labels found in photo.')

    return relevant_labels


def send_data(server_addr, temp, labels, photo):
    if server_addr is None:
        return False

    attempts = 0
    max_attempts = 5

    payload = {'canary_id': canary_id, 'timestamp': get_timestamp(),
               'temperature': temp, 'labels': json.dumps(labels)}

    image = {'image': open(photo, 'rb')}

    url = 'http://' + server_addr + '/post'

    while attempts < max_attempts:
        try:
            r = requests.post(url, data=payload, files=image, timeout=2)
            print(f"[{get_timestamp()}] Event successfully sent to Server")
            if r.text.find('alert') != -1:
                # Server notified user, sleep for 10 min to not spam server+user
                print(f"[{get_timestamp()}] Server notified user about event! Sleeping...")
                time.sleep(600)
            return True
        except requests.exceptions.ConnectionError as e:
            print(f'[{get_timestamp()}] Failed to connect to ServerPi. ', end='')
            attempts += 1
            if attempts == max_attempts and temp >= min_temp_emergency:
                # contact emergency services
                print("Max attempts reached. Contacting emergency services...")
                send_emergency_sms()
                # Sleep for 10 min
                print(f'[{get_timestamp()}] Sleeping...')
                time.sleep(600)
            elif attempts == max_attempts:
                print("Max attempts reached, but temperature reading does not constitute an emergency.")
            else:
                time.sleep(3)  # Sleep 3 seconds, then try sending data again
                print("Retrying...")
    return False


def main():
    server_addr = input('Please enter the ServerPi\'s IP Address: ')
    mm.calibrate()
    try:
        mm.start(on_parked=parked_event, on_moving=moving_event)
        while True:
            if mm.is_parked():
                # Get Temperature
                temp = temp_reader.get_temp()
                print(f'[{get_timestamp()}] Temperature: {temp}°F')
                # Take photo and check for labels
                img_file = take_photo()
                print(f'[{get_timestamp()}] Photo captured: {img_file}')
                relevant_labels = check_photo(img_file)
                # Send to server
                if len(relevant_labels) > 0 and temp >= min_temp_alert:
                    send_data(server_addr, temp, relevant_labels, img_file)
                time.sleep(5)  # Sleep 5 seconds, then take another reading

    finally:
        mm.stop()


if __name__ == "__main__":
    main()
