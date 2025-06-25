from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import json
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta

SCOPES = ["https://www.googleapis.com/auth/calendar"]

REMINDERS_FILE = 'reminders.json'


app = Flask(__name__)
app.secret_key = 'AdminDragon'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

def get_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=51374)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)



#data Storage


def load_reminders():
    if not os.path.exists(REMINDERS_FILE):
        return []
    with open(REMINDERS_FILE, 'r') as f:
        return json.load(f)
def save_reminder(reminder):
    reminders = load_reminders()
    reminder['id'] = str(uuid.uuid4())
    reminders.append(reminder)
    with open(REMINDERS_FILE, 'w') as f:
        json.dump(reminders, f, indent=2)
def get_users_data():
    if not os.path.exists('users.json'):
        return {'users': []}
    with open('users.json', 'r', encoding='utf-8') as f:
        return json.load(f)
def save_users_data(data):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
def get_family_data():
    if not os.path.exists('families.json'):
        return {'families': []}
    with open('families.json', 'r', encoding='utf-8') as f:
        return json.load(f)
def save_family_data(data):
    with open('families.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
def verify_password(stored, provided):
    return check_password_hash(stored, provided)








#index

@app.route('/')
def index():
    return render_template('index.html')




#login

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        data = get_users_data()
        users = data.get('users', [])
        for user in users:
            if user.get('email') == email and verify_password(user.get('password'), password):
                session['user_email'] = email
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
        flash('Invalid email or password!', 'danger')
    return render_template('login.html')


#Dashboard

@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    email = session['user_email']
    users_data = get_users_data()
    current_user = next((u for u in users_data.get('users', []) if u.get('email') == email), None)
    family_id = current_user.get('family_id') if current_user else None
    family_members = [u.get('email') for u in users_data.get('users', []) if u.get('family_id') == family_id and u.get('email') != email]
    reminders = load_reminders()
    user_reminders = [r for r in reminders if r['user_email'] == email or r['family_member_email'] == email]
    return render_template('dashboard.html', user=current_user, family_members_emails=family_members, reminders=user_reminders)



#Signup

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        age = request.form.get('age')
        family_id = request.form.get('family_id')

        users_data = get_users_data()
        users = users_data.get('users', [])

        if any(u.get('email') == email for u in users):
            flash('Email already exists!', 'danger')
            return render_template('signup.html')

        hashed_password = generate_password_hash(password)

        users.append({
            'email': email,
            'password': hashed_password,
            'age': age,
            'family_id': family_id
        })
        users_data['users'] = users

        family_data = get_family_data()
        families = family_data.get('families', [])

        family = next((f for f in families if f['family_id'] == family_id), None)

        if family:
            family['members'].append({
                'email': email,
                'age': age
            })
        else:
            families.append({
                'family_id': family_id,
                'members': [{
                    'email': email,
                    'age': age
                }]
            })

        family_data['families'] = families

        try:
            save_users_data(users_data)
            save_family_data(family_data)
            flash('Account created successfully!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error saving data: {e}")
            flash('An error occurred while saving your data.', 'danger')

    return render_template('signup.html')





#family


@app.route('/family')
def family():
    if request.args:
        return redirect(url_for('family'))
    if 'user_email' not in session:
        return redirect(url_for('login'))
    email = session.get('user_email')
    data = get_users_data()
    current = next((u for u in data.get('users', []) if u.get('email') == email), None)
    if not current:
        flash('User not found', 'danger')
        return redirect(url_for('login'))
    family_id = current.get('family_id')
    family_data = get_family_data()
    family_obj = next((f for f in family_data.get('families', []) if f.get('family_id') == family_id), None)
    if not family_obj:
        flash('Family not found', 'danger')
        return redirect(url_for('dashboard'))
    members = [m for m in family_obj.get('members', []) if m.get('email') != email]
    return render_template('family.html', family_members=members)








@app.route('/add_reminder', methods=['GET', 'POST'])
def add_reminder():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    user_email = session['user_email']
    users = get_users_data().get('users', [])
    current_user = next((u for u in users if u['email'] == user_email), None)
    family_id = current_user.get('family_id') if current_user else None
    family_members = []
    family_data = get_family_data()
    family_obj = next((f for f in family_data.get('families', []) if f.get('family_id') == family_id), None)
    if family_obj:
        family_members = [m['email'] for m in family_obj.get('members', []) if m['email'] != user_email]

    if request.method == 'POST':
        med_name = request.form.get('medName') or 'Paracetamol'
        dose = request.form.get('dose') or '1 pill'
        time_val = request.form.get('time') or '08:00'
        selected_family_email = request.form.get('family_member')

        now_date = datetime.now().date()
        time_obj = datetime.strptime(time_val, "%H:%M")
        start_datetime = datetime.combine(now_date, time_obj.time())
        end_datetime = start_datetime + timedelta(minutes=10)

        start_time = start_datetime.isoformat() + "+03:00"
        end_time = end_datetime.isoformat() + "+03:00"
        reminder = {
            'user_email': user_email,
            'med_name': med_name,
            'dose': dose,
            'time': time_val,
            'family_member_email': selected_family_email
        }
        save_reminder(reminder)

        try:
            service = get_calendar_service()
            event = {
                'summary': f'تناول دواء {med_name}',
                'description': f'جرعة {dose}',
                'start': {'dateTime': start_time, 'timeZone': 'Africa/Cairo'},
                'end': {'dateTime': end_time, 'timeZone': 'Africa/Cairo'},
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 10},
                        {'method': 'popup', 'minutes': 5},
                    ],
                },
            }
            service.events().insert(calendarId='primary', body=event).execute()
        except Exception as e:
            print("Failed to create calendar event:", e)
            flash('Failed to add event to Google Calendar.', 'danger')

        flash('Reminder and calendar event added!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_reminder.html', email=user_email, medName='Paracetamol', dose='1 pill', time_val='08:00', family_members=family_members)











@app.route('/delete_reminder', methods=['POST'])
def delete_reminder():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    reminder_id = request.form.get('reminder_id')
    if not reminder_id:
        flash('Invalid reminder ID!', 'danger')
        return redirect(url_for('dashboard'))
    
    reminders = load_reminders()
    email = session['user_email']

    reminder_to_delete = None
    for r in reminders:
        if r.get('id') == reminder_id and (r.get('user_email') == email or r.get('family_member_email') == email):
            reminder_to_delete = r
            break

    if reminder_to_delete:
        reminders.remove(reminder_to_delete)
        with open(REMINDERS_FILE, 'w') as f:
            json.dump(reminders, f, indent=2)
        flash('Reminder deleted successfully!', 'success')
    else:
        flash('Reminder not found or unauthorized!', 'danger')
    
    return redirect(url_for('dashboard'))



if __name__ == "__main__":
    app.run(debug=True,port=51374)
