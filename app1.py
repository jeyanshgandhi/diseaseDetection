from flask import Flask, render_template, session, url_for, request, flash, redirect, jsonify

import pymongo

from flask_cors import CORS

import random, os, ssl, smtplib

from email.message import EmailMessage

from email.mime.text import MIMEText

from email.mime.image import MIMEImage

from email.mime.multipart import MIMEMultipart


app = Flask(__name__)

CORS(app)


client = pymongo.MongoClient("mongodb://localhost:27017")

db = client['SymptoScan']

doctor_collection = db['doctors']

sympto_collection = db['users']

user_history = db['userHistory']

app.secret_key = 'ThisIsDiseaseDetectorApp'

app.config['SESSION_COOKIE_NAME'] = 'session_doctors'


patients_data = {}


@app.route('/receive_session', methods=['POST'])

def receive_session():

    try:

        session_data = request.json.get('session_data', {})

        doctor_email = request.json.get('doctor_email')


        # Clear patient data for other doctors

        # doctors_to_clear = [email for email in patients_data.keys() if email != doctor_email]

        # for email in doctors_to_clear:

        #     del patients_data[email]


        # Set or append new session_data for the current doctor_email
        if doctor_email not in patients_data:

            patients_data[doctor_email] = []

        patients_data[doctor_email].append(session_data)


        return jsonify({"message": "Session data received"}), 200

    except Exception as e:

        print(f'Error receiving session data: {e}')

        return jsonify({"message": str(e)}), 400



@app.route('/')
def doctor_main():
    print(session)
    if 'demail' not in session:

        return render_template('doctor_main.html', redirect_to_login = True, doctor_collection=doctor_collection)

    return render_template('doctor_main.html', redirect_to_login = False, doctor_collection=doctor_collection)


@app.route('/doctor_register', methods=['GET', 'POST'])

def doctor_register():
    if 'demail' in session:
        return redirect(url_for('main'))


    if request.method == 'POST':

        name = request.form.get('dname')

        email = request.form.get('demail')

        dob = request.form.get('ddob')

        phone = request.form.get('dphone')

        qualification = request.form.get('dqualification')

        speciality = request.form.get('dspeciality')

        experience = request.form.get('dexperience')

        address = request.form.get('daddress')

        password = request.form.get('dpassword')

        cpassword = request.form.get('dcpassword')


        if not name or not email or not dob or not phone or not password or not cpassword:

            flash('Please enter all the details!')

            return redirect(url_for('doctor_register'))


        if len(phone) > 10 or len(phone) < 10:

            flash('Invalid Phone Number!')

            return redirect(url_for('doctor_register'))


        if password != cpassword:

            flash('Passwords do not match!')

            return redirect(url_for('doctor_register'))


        exist = doctor_collection.find_one({'email': email})

        exists = sympto_collection.find_one({'email': email})

        if exist:

            flash("Email already exists as doctor's id!")

            return redirect(url_for('doctor_register'))
        

        if exists:

            flash("Email already exists as user's id!")

            return redirect(url_for('doctor_register'))


        new_user = {

            'name': name,

            'email': email,

            'dob': dob,

            'qualifications': qualification,

            'specialization': speciality,

            'experience': experience,

            'address': address,

            'phone': phone,

            'password': password

        }


        doctor_collection.insert_one(new_user)

        session['demail'] = email
        return redirect(url_for('doctor_main'))

    return render_template('doctor_register.html')


@app.route('/doctor_login', methods=['GET', 'POST'])

def doctor_login():
    if 'demail' in session:

        flash('Already Logged-In')
        return redirect(url_for('doctor_main'))


    if request.method == 'POST':

        email = request.form.get('demail')

        password = request.form.get('dpassword')

        user = doctor_collection.find_one({'email': email})


        if not email or not password:

            flash('Enter details')

            return redirect(url_for('doctor_login'))


        if user and (user['password'] == password):

            session['demail'] = user['email']

            session['name'] = user['name']
            return redirect(url_for('doctor_main'))

            # return render_template('doctor_main.html', doctor_collection = doctor_collection, sympto_collection = sympto_collection)
        else:

            flash('Invalid login details!', "error")

            return render_template('doctor_login.html')

    return render_template('doctor_login.html')


@app.route('/doctor_update', methods=['GET','POST'])
def doctor_update():

    if request.method == "POST":

        name = request.form.get('name')

        email = request.form.get('email')

        dob = request.form.get('dob')

        phone = request.form.get('phone')

        experience = request.form.get('dexperience')

        qualification = request.form.get('dqualification')

        specialization = request.form.get('dspeciality')

        address = request.form.get('daddress')

        if name:

            doctor_collection.update_one({'email': session['demail']}, {'$set': {'name': name}})


        if dob:

            doctor_collection.update_one({'email': session['demail']}, {'$set': {'dob': dob}})


        if phone:

            doctor_collection.update_one({'email': session['demail']}, {'$set': {'phone': phone}})
            

        if experience:

            doctor_collection.update_one({'email': session['demail']}, {'$set': {'experience': experience}})
        

        if qualification:

            doctor_collection.update_one({'email': session['demail']}, {'$set': {'qualification': qualification}})
        

        if specialization:

            doctor_collection.update_one({'email': session['demail']}, {'$set': {'specialization': specialization}})
        
        if address:

            doctor_collection.update_one({'email': session['demail']}, {'$set': {'address': address}})
        return redirect(url_for('doctor_main'))

    return render_template('doctor_update.html', sympto_collection=sympto_collection, doctor_collection = doctor_collection)


@app.route('/logout')

def logout():
    if 'demail' in session:
        session.clear()

        return redirect(url_for('doctor_login'))
    else:

        flash("You are not logged in")

        return redirect(url_for('doctor_login'))


@app.route('/delete')
def delete():
    if 'demail' in session:

        user = session['demail']

        doctor_collection.delete_one({'email': user})
        session.clear()
        return redirect(url_for('doctor_main'))
    return render_template('doctor_main')



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

            doctor = doctor_collection.find_one({'email': session['email']})
            if user or doctor:

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

            doctor = doctor_collection.find_one({'email':session['email']})
            if user:

                sympto_collection.update_one({'email': session['email']}, {'$set': {'password': con_password}})
                session.clear()

                flash('Password Updated Sucessfully!!')
                print(session)

                return redirect(url_for('login'))
            elif doctor:

                doctor_collection.update_one({'email': session['email']}, {'$set': {'password': con_password}})
                session.clear()

                flash('Password Updated Sucessfully!!')
                print(session)

                return redirect(url_for('doctor_login'))
            else:

                flash("User does'not exist!")
                session.clear()
        else:

            flash("Passwords do'not match!")
    

    return render_template('reset_pass.html')



@app.route('/look_patient')
def look_patient():
    session_email = session.get('demail', None)  
    doctors_email = ""
    global patient_profile 
    patient_profile = []
    for Demail,patient in patients_data.items():
        if Demail == session_email:
            doctors_email = Demail
            # print(doctors_email)
            for patientT in patient:
                data_dict = {key: value for key, value in patientT.items()}
                patient_profile.append({
                    'email': data_dict['email'],
                    'prediction': data_dict['prediction'],
                    'phone': data_dict['phone'],
                    'date': data_dict['date'],
                    'name': data_dict['name']
                })
    # print(patient_profile)
    if doctors_email == session_email and doctors_email != "":
        # print('yes it matched')
        return render_template('look_patient.html', doctors_email=doctors_email, patient_profile = patient_profile)
    return render_template('look_patient.html')

@app.route('/done', methods=['POST'])
def done():
    try:
        prediction = request.form.get('prediction')
        date = request.form.get('date')
        session_email = session.get('demail', None)

        if session_email in patients_data or date in patients_data:
            for patient in patients_data[session_email]:
                if patient['prediction'] == prediction and patient['date'] == date:
                    patients_data[session_email].remove(patient)
                    break
            user = user_history.find_one({'doctor_email': session_email, 'date': date})
            if user:
                user_history.update_one({'doctor_email':session_email, 'date':date}, {"$set":{'status':'accepted'}})
        return redirect(url_for('look_patient'))
    
    except Exception as e:
        print(f'Error deleting patient profile: {e}')
        return redirect(url_for('look_patient'))

@app.route('/reject', methods=['POST'])
def reject():
    try:
        prediction = request.form.get('prediction')
        date = request.form.get('date')
        session_email = session.get('demail', None)
        if session_email in patients_data or date in patients_data:
            for patient in patients_data[session_email]:
                if patient['prediction'] == prediction and patient['date'] == date:
                    patients_data[session_email].remove(patient)
                    break

            user = user_history.find_one({'doctor_email': session_email, 'date': date})
            if user:
                user_history.update_one({'doctor_email':session_email, 'date':date}, {"$set":{'status':'rejected'}})
        return redirect(url_for('look_patient'))

    except Exception as e:
        print(f'Error deleting patient profile: {e}')
        return redirect(url_for('look_patient'))

@app.route('/doctorHistory')
def doctorHistory():
    email = session['demail']
    doctors = user_history.find({'doctor_email':email})
    return render_template('doctorHistory.html', doctors=doctors)

@app.route('/prescribes', methods=['GET','POST'])
def prescribes():
    prediction = request.form.get('prediction')
    date = request.form.get('date')
    email = session['demail']
    session['PreditioN'] = prediction
    session['DatE'] = date
    if email in session:
        return render_template('prescribe.html', patient_profile = patient_profile, prediction = prediction, date = date)

    return render_template('prescribe.html')

@app.route('/prescribe', methods=['GET','POST'])
def prescribe():
    prediction = session['PreditioN']
    date = session['DatE']
    email = session['demail']
    counter = int(request.form.get('counter'))
    print(prediction, date, email, counter)
    value = {}
    prescribe = []
    if request.method == 'POST':
        for i in range(1, counter+1):
            key = f"prescribe{i}"
            prescription = request.form.get(key)
            if prescription:
                prescribe.append(prescription)
        user = user_history.find_one({'doctor_email':email, 'date': date})
        if user:
            user_history.update_one({'doctor_email':email, 'date': date}, {"$set":{'prescription':prescribe}})
        return redirect(url_for('look_patient'))
    
    return render_template('prescribe.html', prediction = prediction, date = date)

if __name__ == '__main__':
    app.run(debug=True, port=5001)