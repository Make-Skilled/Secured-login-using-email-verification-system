from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Markup
import smtplib
import random
import string
from pymongo import MongoClient
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change this to a strong secret in production

# Hardcoded MongoDB Atlas URI (replace with your actual URI)
MONGO_URI = 'mongodb+srv://gnana1313:Gnana1212@dbs.8wngtib.mongodb.net/?retryWrites=true&w=majority&appName=DBs'
client = MongoClient(MONGO_URI)
db = client['password_bucket']
users_col = db['users']
passwords_col = db['passwords']

# Email configuration (replace with your actual email and app password)
EMAIL_ADDRESS = 'hellopythonhere@gmail.com'
EMAIL_PASSWORD = 'uhex ufof seya lxuz'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

def send_verification_email(to_email, code):
    subject = 'Your Password Bucket Verification Code'
    body = f'Your verification code is: {code}'
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print('Email send failed:', e)
        return False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    message = None
    success = False
    code_sent = False
    registered = False
    name = email = password = ''
    if request.method == 'POST':
        if 'code' not in request.form:
            # First form submission: send code
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            if users_col.find_one({'email': email}):
                message = 'Email already registered. Please login.'
            else:
                code = ''.join(random.choices(string.digits, k=6))
                session['signup_code'] = code
                session['signup_name'] = name
                session['signup_email'] = email
                session['signup_password'] = password
                if send_verification_email(email, code):
                    code_sent = True
                    message = f'Verification code sent to {email}.'
                else:
                    message = 'Failed to send verification email. Please try again.'
        else:
            # Second form submission: verify code
            code = request.form['code']
            name = session.get('signup_name', '')
            email = session.get('signup_email', '')
            password = session.get('signup_password', '')
            if code == session.get('signup_code'):
                # Register user
                hashed_pw = generate_password_hash(password)
                users_col.insert_one({'name': name, 'email': email, 'password': hashed_pw})
                message = 'Registration successful! You can now login.'
                success = True
                registered = True
                # Clear session data
                session.pop('signup_code', None)
                session.pop('signup_name', None)
                session.pop('signup_email', None)
                session.pop('signup_password', None)
            else:
                message = 'Invalid code. Signup cancelled.'
                # Clear session data
                session.pop('signup_code', None)
                session.pop('signup_name', None)
                session.pop('signup_email', None)
                session.pop('signup_password', None)
    else:
        # GET request
        session.pop('signup_code', None)
        session.pop('signup_name', None)
        session.pop('signup_email', None)
        session.pop('signup_password', None)
    return render_template('signup.html', message=message, success=success, code_sent='signup_code' in session, registered=registered, name=name, email=email, password=password)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    message = None
    show_section = 'store'
    # Handle add password
    if request.method == 'POST' and 'add_entry' in request.form:
        site = request.form['site']
        account_username = request.form['account_username']
        pw = request.form['password']
        passwords_col.insert_one({'user_id': user_id, 'site': site, 'account_username': account_username, 'password': pw})
        return redirect(url_for('dashboard', msg='created'))
    # Handle delete
    if request.method == 'POST' and 'delete_entry' in request.form:
        entry_id = request.form['delete_entry']
        passwords_col.delete_one({'_id': ObjectId(entry_id), 'user_id': user_id})
        return redirect(url_for('dashboard', msg='deleted', section='view'))
    # Handle flash messages and section
    msg = request.args.get('msg')
    if msg == 'created':
        message = 'Password saved successfully.'
        show_section = 'store'
    elif msg == 'deleted':
        message = 'Password deleted successfully.'
        show_section = 'view'
    section = request.args.get('section')
    if section:
        show_section = section
    entries = list(passwords_col.find({'user_id': user_id}))
    return render_template('dashboard.html', entries=entries, user_name=session.get('user_name'), message=message, show_section=show_section)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users_col.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            return redirect(url_for('dashboard'))
        else:
            message = 'Invalid email or password.'
    return render_template('login.html', message=message) 

if __name__ == '__main__':
    app.run(debug=True) 