from flask import Flask, request, render_template, redirect, make_response
import pymongo

# Flask
WEBAPP_PORT = 80
app = Flask("ServerPi")

# MongoDB
g_user_col = None


# ------------------- MongoDB - Events --------------------

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


# ---------------------- Canary Comm ----------------------

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
    temp_alert = request.form['temp_alert']

    if update_user(username, baby_alert, pet_alert, phone_number, temp_alert):
        return make_settings_resp(username, password, "success", "Changes processed.")
    else:
        return make_settings_resp(username, password, "error", "An error occurred.")


def main():
    setup_userDB()
    app.run(host="0.0.0.0", port=WEBAPP_PORT)


if __name__ == '__main__':
    main()
