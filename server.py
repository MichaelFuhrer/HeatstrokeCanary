from flask import Flask, request, render_template, redirect, make_response
from lib.rekognition.rekognition_image_detection import RekognitionImage
import boto3
import pymongo
import base64
import keys
import json
from datetime import datetime  # For console print timestamps
from twilio.rest import Client


# Flask
port = 80
app = Flask("ServerPi")

# MongoDB
g_user_col = None
g_event_col = None

# Rekognition client and alert labels
rekognition_client = boto3.client('rekognition',
                                  aws_access_key_id=keys.aws_access_id,
                                  aws_secret_access_key=keys.aws_secret_id,
                                  region_name='us-east-1')
baby_alert_labels = ['Baby', 'Person']
pet_alert_labels = ['Dog', 'Pet']

min_temp_alert = 80


def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")


# ------------------- Server Functions --------------------

def check_event(username, temperature, labels):
    baby_alert = False
    pet_alert = False

    for label in labels:
        if not baby_alert and label[0] in baby_alert_labels:
            baby_alert = True
        if not pet_alert and label[0] in pet_alert_labels:
            pet_alert = True

    if temperature > get_user_value(username, "temp_alert"):
        if (baby_alert and get_user_value(username, 'baby_alert')) or (
                pet_alert and get_user_value(username, 'pet_alert')):
            return True
    return False


def send_notification(username, temperature, labels):
    user_phone = get_user_value(username, 'phone_number')
    print(f'[{get_timestamp()}] Sending notification to {username} @ {user_phone}')

    client = Client(keys.twilio_sid, keys.twilio_auth)

    message = f"Alert {username}! A temperature of {temperature}°F was recorded in your vehicle while a " \
              f"{labels[0][0]} (Confidence of {labels[0][1]}%) is inside. Please take appropriate action to ensure " \
              f"they are safe."

    client.messages.create(body=message, from_=keys.twilio_phone, to=user_phone)


# ------------------- MongoDB - Events --------------------
def setup_eventDB():
    global g_event_col
    event_db_client = pymongo.MongoClient("mongodb://localhost:27017/")
    event_db = event_db_client["HeatstrokeCanary"]
    g_event_col = event_db["events"]


def record_event(canary_id, timestamp, temperature, labels, image):
    new_event = {
        "canary_id": canary_id,
        "timestamp": timestamp,
        "temperature": temperature,
        "labels": labels,
        "image": image
    }

    g_event_col.insert_one(new_event)
    return True


# ---------------- MongoDB - Authentication ---------------

def setup_userDB():
    global g_user_col
    user_db_client = pymongo.MongoClient("mongodb://localhost:27017/")
    user_db = user_db_client["HeatstrokeCanary"]
    g_user_col = user_db["users"]


def register_user(username, password, device_id, phone_number):
    # Make sure user doesn't already exist
    result = g_user_col.find_one("username", username)
    if result is not None:
        return False  # User already exists

    new_user = {
        "username": username,
        "password": password,
        "device_id": device_id,
        "baby_alert": True,
        "pet_alert": True,
        "phone_number": phone_number,
        "temp_alert": 80
    }
    g_user_col.insert_one(new_user)
    return True


def update_user(username, baby_alert: bool, pet_alert: bool, phone_number: str, temp_alert: int):
    # Set new values
    new_values = {"$set": {
        "baby_alert": baby_alert,
        "pet_alert": pet_alert,
        "phone_number": phone_number,
        "temp_alert": temp_alert
    }}
    result = g_user_col.update_one({"username": username}, new_values)
    if result is None:
        return False  # User not found

    return True


def verify_user(username, password):
    result = g_user_col.find_one({"username": username})
    if result is not None and result["password"] == password:
        return True
    return False


def get_user_value(username, setting):
    result = g_user_col.find_one({"username": username})
    if result is not None:
        return result[setting]
    return None


def find_user(canary_id):
    result = g_user_col.find_one({"device_id": canary_id})
    if result is not None:
        return result["username"]
    return None


# ---------------------- Canary Comm ----------------------

@app.route("/post", methods=['POST'])
def post():
    canary_id = request.form.get('canary_id')
    timestamp = request.form['timestamp']
    temperature = int(request.form['temperature'])
    relevant_labels = json.loads(request.form['labels'])
    image = request.files.get('image')

    # Print out info
    print(f'[{get_timestamp()}] Received post from {canary_id}:')
    print(f'\t{timestamp}, {temperature}°F, {image.filename}')
    print(f'\tRelevant labels:')
    for entry in relevant_labels:
        print(f'\t{entry}')

    # Save image locally
    image.save(f'./captures/{image.filename}')

    username = find_user(canary_id)
    if username is None:
        print(f'[{get_timestamp()}] Device ID was not recognized')
        return "Device ID not recognized", 400  # Bad request

    record_event(canary_id, timestamp, temperature, relevant_labels, image.filename)
    if check_event(username, temperature, relevant_labels):
        send_notification(username, temperature, relevant_labels)
        return "Event processed, alert sent", 200  # POST Okay
    return "Event processed", 200  # POST Okay


# ------------------------ WEB-GUI ------------------------

@app.route('/', methods=['GET'])
def web_page_redirect():
    return redirect('/login')


@app.route('/login')
def login_page():
    return render_template('login_page.html',
                           notification_style="hide",
                           notification_text="")


@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']
    # User validation
    if verify_user(username, password):
        # User verified - Make a cookie w/ user data and redirect to settings
        resp = make_response(redirect('/settings'))
        resp.set_cookie('username', username)
        resp.set_cookie('password', password)
        return resp
    else:
        return render_template('login_page.html',
                               notification_style="error",
                               notification_text="Invalid login.")


@app.route('/signup')
def signup_page():
    return render_template('signup_page.html',
                           notification_style="hide",
                           notification_text="")


@app.route('/signup', methods=['POST'])
def signup_post():
    username = request.form['username']
    password = request.form['password']
    device_id = request.form['device_id']
    phone_number = request.form['phone_number']
    # Register user, check to user not a duplicate
    if register_user(username, password, device_id, phone_number):
        # Successful registration - Make a cookie w/ user data
        resp = make_response(redirect('/settings'))
        resp.set_cookie('username', username)
        resp.set_cookie('password', password)
        return resp
    else:
        # Unsuccessful registration
        return render_template('signup_page.html',
                               notification_style="error",
                               notification_text="User with that username already exists.")


def make_settings_resp(username, password, notification_style="hide", notification_text=""):
    baby_alert_old = ""
    if get_user_value(username, 'baby_alert'):
        baby_alert_old = "checked"

    pet_alert_old = ""
    if get_user_value(username, 'pet_alert'):
        pet_alert_old = "checked"

    resp = make_response(render_template('settings_page.html',
                                         username=username,
                                         device_id=get_user_value(username, 'device_id'),
                                         baby_alert_old=baby_alert_old,
                                         pet_alert_old=pet_alert_old,
                                         phone_number_old=get_user_value(username, 'phone_number'),
                                         temp_alert_old=get_user_value(username, 'temp_alert'),
                                         notification_style=notification_style,
                                         notification_text=notification_text))
    resp.set_cookie('username', username)
    resp.set_cookie('password', password)
    return resp


@app.route('/settings')
def settings_page():
    username = request.cookies.get('username')
    password = request.cookies.get('password')

    if not verify_user(username, password):
        return "Invalid login", 400  # Bad request

    return make_settings_resp(username, password)


@app.route('/settings', methods=['POST'])
def settings_post():
    username = request.cookies.get('username')
    password = request.cookies.get('password')

    if not verify_user(username, password):
        return "Invalid login", 400  # Bad request

    baby_alert = request.form.get('baby_alert') == 'on'
    pet_alert = request.form.get('pet_alert') == 'on'
    phone_number = request.form['phone_number']
    temp_alert = int(request.form['temp_alert'])

    if temp_alert < min_temp_alert and update_user(username, baby_alert, pet_alert, phone_number, min_temp_alert):
        return make_settings_resp(username, password, "alert",
                                  f"Changes processed. Attention: Minimum alert temperature is {min_temp_alert}°F.")
    elif update_user(username, baby_alert, pet_alert, phone_number, temp_alert):
        return make_settings_resp(username, password, "success", "Changes processed.")
    else:
        return make_settings_resp(username, password, "error", "An error occurred.")


def main():
    setup_eventDB()
    setup_userDB()
    app.run(host="0.0.0.0", port=port)


if __name__ == '__main__':
    main()
