from lib.rekognition.rekognition_image_detection import RekognitionImage
import boto3
from motion_monitor import motion_monitor
import time
from picamera import PiCamera
import keys
import os

label_flags = ['Baby', 'Pet', 'Dog', 'Person']

# Set up Rekognition client
rekognition_client = boto3.client('rekognition',
                                  aws_access_key_id=keys.access_id,
                                  aws_secret_access_key=keys.secret_id,
                                  region_name='us-east-1')
mm = motion_monitor()
camera = PiCamera()


def parked_event():
    print("Car is parked.")


def moving_event():
    print("Car is moving.")


def check_camera():
    # Take photograph
    timestamp = time.time()
    image_file = f'./captures/capture-{timestamp}.jpg'
    camera.capture(image_file)
    # Use photograph to determine whether there is a baby or dog in photo
    rekognition = RekognitionImage.from_file(image_file, rekognition_client)
    labels = rekognition.detect_labels(10)
    label_dict = {label.name: label.confidence for label in labels}
    print(label_dict)

    for flag in label_flags:
        if flag in label_dict:
            return [flag, label_dict[flag], image_file]

    os.remove(image_file)
    return None

# Canary -> Server: temperature & photo
# Temperature -- userset temp threshold
# Photo -> Rekognition -- userset boolean values

def main():
    mm.calibrate()

    try:
        mm.start(on_parked=parked_event, on_moving=moving_event)
        while True:
            if mm.is_parked():
                print("Checking sensors...")
                # Get Temperature todo
                # Check Camera
                cam_object = check_camera()
                if check_camera() is not None:
                    print("!"*25, cam_object, "!"*25)
                time.sleep(1)

    finally:
        mm.stop()


if __name__ == "__main__":
    main()
