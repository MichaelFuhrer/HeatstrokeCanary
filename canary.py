
from motion_monitor import motion_monitor
import time
from picamera import PiCamera
import os

mm = motion_monitor()
camera = PiCamera()


def parked_event():
    print("Car is parked.")


def moving_event():
    print("Car is moving.")


def take_photo():
    # Take photograph
    timestamp = time.time()
    image_file = f'./captures/capture-{timestamp}.jpg'
    camera.capture(image_file)
    return image_file


def main():
    mm.calibrate()

    try:
        mm.start(on_parked=parked_event, on_moving=moving_event)
        while True:
            if mm.is_parked():
                print("Checking sensors...")
                # Get Temperature todo
                # Take photo
                # Send to server
                time.sleep(1)

    finally:
        mm.stop()


if __name__ == "__main__":
    main()
