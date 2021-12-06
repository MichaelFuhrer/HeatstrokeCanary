from flask import Flask, request, render_template, redirect, make_response

app = Flask("ServerPi")


@app.route('/', methods=['GET'])
def web_page_redirect():
    return redirect('/login')


@app.route('/login')
def login_page():
    return render_template('login_page.html')


@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']
    # todo validate user
    print(f'Username: {username} Password: {password}')
    # Make a cookie w/ user data
    resp = make_response(render_template('settings_page.html', username=username, device_id="12345"))
    resp.set_cookie('username', username)
    resp.set_cookie('password', password)
    return resp


@app.route('/settings', methods=['POST'])
def settings_post():
    username = request.cookies.get('username')
    password = request.cookies.get('password')
    baby_alert = request.form.get('baby_alert') == 'on'
    pet_alert = request.form.get('pet_alert') == 'on'
    phone_number = request.form['phone_number']
    temp_alert = request.form['temp_alert']
    print(f'Username: {username} Password: {password} Phone #: {phone_number}')
    print(f'Alert on baby: {baby_alert} & pet: {pet_alert} @ {temp_alert}°F')


def main():
    app.run(host="0.0.0.0", port=80)


if __name__ == '__main__':
    main()
