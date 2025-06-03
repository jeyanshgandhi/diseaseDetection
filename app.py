from flask import Flask, render_template, session, url_for, request, flash, redirect, jsonify
import pymongo
import joblib
import numpy as np
from scipy.stats import mode
import smtplib, ssl
import os, requests
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import re, random
from datetime import datetime


app = Flask(__name__)
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client['SymptoScan']
sympto_collection = db['users']
user_history = db['userHistory']
doctor_collection = db['doctors']
app.secret_key = 'ThisIsDiseaseDetectorApp'

rfc_model = joblib.load('models/rfc_model.pkl')
gnb_model = joblib.load('models/gnb_model.pkl')
svc_model = joblib.load('models/svc_model.pkl')

# Load the data dictionary
data_dict = joblib.load('models/data_dict.pkl')

@app.route('/set_session', methods=['POST'])
def set_session():
    session['data'] = request.json.get('data')
    return jsonify({"message": "Session data set"}), 200

@app.route('/send_session_to_doctor', methods=['POST'])
def send_session_to_doctor():
    date = datetime.now()
    date_str = date.strftime("%Y/%m/%d %H:%M:%S %z")
    session['date'] = date_str
    doctor_email = request.json.get('doctor_email')
    session_data = dict(session)
    
    print(date_str)

    try:
        # Send session data to the application on port 5001
        response = requests.post('http://localhost:5001/receive_session', json={
            'doctor_email': doctor_email,
            'session_data': session_data,
            'date': date_str
        })
        print(response)
        if response.status_code == 200:
            doctor_name = doctor_collection.find_one({'email':doctor_email})
            new_history = {
                'doctor_email': doctor_email,
                'patient_name': session['name'],
                'user-email': session['email'],
                'symptom-1': session['symptom-1'],
                'symptom-2': session['symptom-2'],
                'symptom-3': session['symptom-3'],
                'symptom-4': session['symptom-4'],
                'disease': session['prediction'],
                'status': 'pending',
                'date': date_str,
                'doctor_name': doctor_name['name']
            }
            user_history.insert_one(new_history)
            return jsonify({"message": "Session data sent successfully"}), 200
        else:
            return jsonify({"message": "Failed to send session data"}), response.status_code
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/')
def main():
    print(session)
    if 'email' not in session:
        return render_template('main.html', redirect_to_login=True, sympto_collection=sympto_collection)
    return render_template('main.html', redirect_to_login=False, sympto_collection=sympto_collection)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'email' in session:
        return redirect(url_for('main'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        dob = request.form.get('dob')
        phone = request.form.get('phone')
        password = request.form.get('password')
        cpassword = request.form.get('cpassword')

        if not name or not email or not dob or not phone or not password or not cpassword:
            flash('Please enter all the details!')
            return redirect(url_for('register'))

        if len(phone) > 10 or len(phone) < 10:
            flash('Invalid Phone Number!')
            return redirect(url_for('register'))

        if password != cpassword:
            flash('Passwords do not match!')
            return redirect(url_for('register'))

        exist = sympto_collection.find_one({'email': email})
        exists = doctor_collection.find_one({'email': email})
        if exist:
            flash("Email already exists as user's id!")
            return redirect(url_for('register'))
        if exists:
            flash("Email already exists as doctor's id!")
            return redirect(url_for('register'))
        
        new_user = {
            'name': name,
            'email': email,
            'dob': dob,
            'phone': phone,
            'password': password
        }

        sympto_collection.insert_one(new_user)
        session['email'] = email
        session['phone'] = phone
        return redirect(url_for('main'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'email' in session:
        flash('Already Logged-In')
        return redirect(url_for('main'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = sympto_collection.find_one({'email': email})

        if not email or not password:
            flash('Enter details')
            return redirect(url_for('login'))

        if user and (user['password'] == password):
            session['email'] = user['email']
            session['phone'] = user['phone']
            session['name'] = user['name']
            return redirect(url_for('main'))
        else:
            flash('Invalid login details!', "error")
            return render_template('login.html')

    return render_template('login.html')

@app.route('/forgot_pass', methods=['GET', 'POST'])
def forgot_pass():
    if request.method == 'POST':
        form_id = request.form.get('form_id')
        
        if form_id == "form1":  
            otp = random.randint(100000, 999999)
            session['sent_otp'] = otp      
            os.environ['EMAIL_PASSWORD'] = 'bkvc xyog rdoj uoak'
            sender = 'jeyansh10@gmail.com'
            password = os.environ.get("EMAIL_PASSWORD")
            receiver = request.form.get('email')
            session['email'] = receiver
            body = f"Your password reset otp is: {otp}"
            context = ssl.create_default_context()
            me = EmailMessage()
            me['To'] = receiver
            me['From'] = sender
            me['Subject'] = 'Reset Password'
            me.set_content(body)
            user = sympto_collection.find_one({'email': session['email']})
            if user:
                try:
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
                        smtp.login(sender, password)
                        smtp.sendmail(sender, receiver, me.as_string())
                        print(f'Email sent successfully! {receiver}', otp)
                except Exception as e:
                    flash('Error occured please attempt after sometime!')
                    print("An error occurred while sending the email:", e)
                    session.clear()
            else:
                session.clear()
                flash("User does'not exist!")
                
        elif form_id == 'form2':
            receive_otp = request.form.get('received_otp')
            if 'sent_otp' in session and receive_otp == str(session['sent_otp']):
                print(session, receive_otp)
                return redirect(url_for('reset_pass'))
            else:
                flash('Enter valid otp')
    return render_template('forgot_pass.html')

@app.route('/reset_pass', methods=['GET', 'POST'])
def reset_pass():
    if request.method == 'POST':
        password = request.form.get('password')
        con_password = request.form.get('cpassword')
        if password == con_password:
            user = sympto_collection.find_one({'email': session['email']})
            if user:
                sympto_collection.update_one({'email': session['email']}, {'$set': {'password': con_password}})
                session.clear()
                flash('Password Updated Sucessfully!!')
                print(session)
                return redirect(url_for('login'))
            else:
                flash("User does'not exist!")
                session.clear()
        else:
            flash("Passwords do'not match!")
    
    return render_template('reset_pass.html')


@app.route('/update', methods=['GET','POST'])
def update():
    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        dob = request.form.get('dob')
        phone = request.form.get('phone')

        if name:
            sympto_collection.update_one({'email': session['email']}, {'$set': {'name': name}})

        if dob:
            sympto_collection.update_one({'email': session['email']}, {'$set': {'dob': dob}})

        if phone:
            sympto_collection.update_one({'email': session['email']}, {'$set': {'phone': phone}})
        return redirect(url_for('main'))
    return render_template('update.html', sympto_collection=sympto_collection)

@app.route('/delete')
def delete():
    if 'email' in session:
        user = session['email']
        sympto_collection.delete_one({'email': user})
        session.clear()
        return redirect(url_for('main'))
    return render_template('main')

@app.route('/logout')
def logout():
    if 'email' in session:
        session.clear()
        return redirect(url_for('login'))
    else:
        flash("You are not logged in")
        return redirect(url_for('login'))

@app.route('/check_disease', methods=['GET', 'POST'])
def check_disease():
    
    if 'email' in session:
        if request.method == 'POST':
            # Get form data
            symptom1 = request.form.get('symptom-1', "").strip()
            symptom2 = request.form.get('symptom-2', "").strip()
            symptom3 = request.form.get('symptom-3', "").strip()
            symptom4 = request.form.get('symptom-4', "").strip()

            session['symptom-1'] = symptom1
            session['symptom-2'] = symptom2
            session['symptom-3'] = symptom3
            session['symptom-4'] = symptom4
            
            
            
            # Validate if any symptoms are provided
            if symptom1 or symptom2 or symptom3 or symptom4:
                # Convert symptoms to features                
                symptoms = [symptom1, symptom2, symptom3, symptom4]
                features = preprocess(symptoms)

                # Make predictions with each model
                svc_pred = svc_model.predict(features)[0]
                gaussiannb_pred = gnb_model.predict(features)[0]
                randomforest_pred = rfc_model.predict(features)[0]

                # Combine predictions
                combined_pred = [svc_pred, gaussiannb_pred, randomforest_pred]

                # Determine the majority vote
                final_pred = mode(combined_pred, axis=0, keepdims=True)[0][0]

                prediction_text = data_dict["predictions_classes"][final_pred]
                session['prediction'] = prediction_text
                print(session)
                return render_template('check_disease.html', prediction=prediction_text, sympto_collection = sympto_collection, doctor_collection = doctor_collection)
            else:
                session['prediction'] = 'None'
                # flash("Please provide all symptoms in the form.")
                return render_template('check_disease.html', prediction = session['prediction'])
        else:
            return render_template('check_disease.html')
    else:
        return redirect(url_for('login'))

def preprocess(symptoms):
    symptom_index = data_dict["symptom_index"]
    input_data = [0] * len(symptom_index)

    for symptom in symptoms:
        standardized_symptom = " ".join([word.capitalize() for word in symptom.split()])
        if standardized_symptom in symptom_index:
            index = symptom_index[standardized_symptom]
            input_data[index] = 1
        else:
            print(f"Symptom '{symptom}' not found in symptom index. Skipping.")

    return np.array(input_data).reshape(1, -1)

@app.route('/result')
def result():
    prediction = session.get('prediction')

    # Query the doctors collection for any doctor with specialization containing the prediction
    doctors_cursor = doctor_collection.find({"specialization": {"$regex": prediction, "$options": "i"}})

    doctors = list(doctors_cursor)
    print(doctors)
    
    return render_template('result.html', prediction=prediction, doctors=doctors, sympto_collection = sympto_collection)

@app.route('/userHistory')
def userHistory():
    email = session['email']
    users = user_history.find({'user-email':email})
    return render_template('userHistory.html', user_history=user_history, users=users)


if __name__ == '__main__':
    app.run(debug=True)
    