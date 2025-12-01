
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, current_app
from datetime import datetime, date
import os
import sqlite3
from models import db, User, Patient, Doctor, Appointment , Availability

app = Flask(__name__)
app.config['SECRET_KEY'] = 'demo@1920'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + os.path.join(BASE_DIR, "instance", "hospital.db").replace("\\", "/")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#init
db.init_app(app)


#--helper:map role to dashboard endpoint
def dashboard_for_role(role):
    if role == 'admin':
        return 'admin_dashboard'
    if role == 'doctor':
        return 'doctor_dashboard'
    return 'patient_dashboard'

#----
#HOME
#----   
@app.route('/')
def home():
    if session.get('user_id') and session.get('role'):
        return redirect(url_for(dashboard_for_role(session.get('role'))))
    return render_template('home.html')

#----
#AUTH
#----
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        else:
            return redirect(url_for('patient_dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not email or not password:
            flash('Please enter both email and password.', 'warning')
            return redirect(url_for('login'))
        #find user by email
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('No account found with that email.', 'danger')
            return redirect(url_for('login'))
        if not user.is_active:
            flash("This account has been deactivated. Contact admin.", "danger")
            return redirect(url_for('login'))
        #check pass hash
        if not user.check_password(password):
            flash('Incorrect password.', 'danger')
            return redirect(url_for('login'))
        #login success
        session['user_id'] = user.id
        #store role string
        session['role'] = getattr(user, 'role', 'patient')
        flash('Logged in successfully.', 'success')
        #redirect acc to role
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session['role'] == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        else:
            return redirect(url_for('patient_dashboard'))
    # get req 
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '') 
        confirm_password = request.form.get('confirm_password', '') 
        role = request.form.get('role', 'patient').strip().lower()
        #patient specific
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', '').strip()
        contact = request.form.get('contact', '').strip()
        address = request.form.get('address', '').strip()
        #basic validation
        if not name or not email or not password or not confirm_password:
            flash('Please fill in all required fields (name, email, password).', 'warning')
            return redirect(url_for('register'))
        if password != confirm_password:
            flash('Password do not match.', 'danger')
            return redirect(url_for('register'))
        #check if already exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('An account with that email already exists. Please login or use another email.', 'danger')
            return redirect(url_for('register'))
        #create user
        try:
            user = User(name=name, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            if role == 'patient':
                try:
                    age_val = int(age) if age else None
                except ValueError:
                    age_val = None
                patient = Patient(
                    user_id=user.id,
                    age=age_val,
                    gender=gender if gender else None,
                    contact=contact if contact else None,
                    address=address if address else None
                )
                db.session.add(patient)
            db.session.commit()
            flash('Registration successful. You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the account. Please try again.', 'danger')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

#-----
#ADMIN
#-----
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Admin access required.", "danger")
        return redirect(url_for('login'))
    total_doctors = Doctor.query.count()
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()
    recent_appointments = Appointment.query.order_by(Appointment.date.desc(), Appointment.time.desc()).limit(10).all()
    return render_template('admin_dashboard.html', total_doctors=total_doctors, total_patients=total_patients, total_appointments=total_appointments, recent_appointments=recent_appointments)
@app.route('/admin/manage_doctors', methods=['GET', 'POST'])
def manage_doctors():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Admin access required.", "danger")
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        specialization = request.form.get('specialization', '').strip()
        contact = request.form.get('contact', '').strip()
        if not name or not email:
            flash('Name and email are required to add a doctor.', 'warning')
            return redirect(url_for('manage_doctors'))
        if User.query.filter_by(email=email).first():
            flash('A user with that email already exists.', 'danger')
            return redirect(url_for('manage_doctors'))
        try:
            pw = password if password else 'changeme123'
            user = User(name=name, email=email, role='doctor')
            user.set_password(pw)
            db.session.add(user)
            db.session.flush()
            doctor = Doctor(user_id=user.id,
                            specialization=specialization if specialization else None,
                            contact=contact if contact else None)
            db.session.add(doctor)
            db.session.commit()
            flash('Doctor added successfully.', 'success')
            return redirect(url_for('manage_doctors'))
        except Exception as e:
            db.session.rollback()
            flash('Failed to add doctor. Try again.', 'danger')
            return redirect(url_for('manage_doctors'))
    doctors = Doctor.query.all()
    return render_template('manage_doctors.html', doctors=doctors)
@app.route('/admin/delete_patient/<int:patient_id>', methods=['POST'])
def admin_delete_patient(patient_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Admin access required.", "danger")
        return redirect(url_for('login'))
    patient = Patient.query.get(patient_id)
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for('manage_patients'))
    try:
        db.session.delete(patient)
        db.session.commit()
        flash("Patient deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting patient: {str(e)}", "danger")
    return redirect(url_for('manage_patients'))
    
@app.route('/admin/toggle_user_active/<int:user_id>', methods=['POST'])
def admin_toggle_user_active(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Admin access required.", "danger")
        return redirect(url_for('login'))
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(request.referrer or url_for('admin_dashboard'))
    if user.id == session.get('user_id'):
        flash("You cannot deactivate your own account.", "warning")
        return redirect(request.referrer or url_for('admin_dashboard'))
    try:
        user.is_active = not user.is_active
        db.session.commit()
        flash("User reactivated." if user.is_active else "User deactivated (blacklisted).", "success")
    except Exception:
        db.session.rollback()
        flash("Error updating user status.", "danger")
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/admin/manage_patients', methods=['GET', 'POST'])
def manage_patients():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Admin access required.", "danger")
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', '').strip()
        contact = request.form.get('contact', '').strip()
        address = request.form.get('address', '').strip()
        if not name or not email:
            flash('Name and email are required to add a patient.', 'warning')
            return redirect(url_for('manage_patients'))
        if User.query.filter_by(email=email).first():
            flash('A user with that email already exists.', 'danger')
            return redirect(url_for('manage_patients'))
        try:
            user = User(name=name, email=email, role='patient')
            user.set_password(password if password else 'patient123')
            db.session.add(user)
            db.session.flush()
            try:
                age_val = int(age) if age else None
            except ValueError:
                age_val = None
            patient = Patient(
                user_id=user.id,
                age=age_val,
                gender=gender if gender else None,
                contact=contact if contact else None,
                address=address if address else None
            )
            db.session.add(patient)
            db.session.commit()
            flash('Patient added successfully.', 'success')
            return redirect(url_for('manage_patients'))
        except Exception:
            db.session.rollback()
            flash('Error adding patient. Try again.', 'danger')
            return redirect(url_for('manage_patients'))
    patients = Patient.query.all()
    return render_template('manage_patients.html', patients=patients)
@app.route('/admin/view_all_appointments')
def view_all_appointments():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('login'))
    appointments = Appointment.query.order_by(Appointment.date, Appointment.time).all()
    return render_template('view_all_appointments.html', appointments=appointments)
@app.route('/admin/view_patient_history')
def admin_view_patient_history():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Admin access required.", "danger")
        return redirect(url_for('login'))
    patient_id = request.args.get('patient_id')
    if not patient_id:
        flash('No patient selected.', 'warning')
        return redirect(url_for('admin_dashboard'))
    patient = Patient.query.get(patient_id)
    if not patient:
        flash('Patient not found.', 'danger')
        return redirect(url_for('admin_dashboard'))
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.date, Appointment.time).all()    
    return render_template('view_patient_history.html', patient=patient, appointments=appointments)

#---------
#DR.ROUTES
#---------
@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash("Doctor access required.", "danger")
        return redirect(url_for('login'))
    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    if not doctor:
        flash('Doctor profile not found.', 'danger')
        return redirect(url_for('login'))
    today = date.today()
    appointments = Appointment.query.filter_by(
        doctor_id=doctor.id,
        date=today
    ).order_by(Appointment.time).all()
    return render_template('doctor_dashboard.html', doctor=doctor, appointments=appointments)
@app.route('/doctor/complete_appointment', methods=['GET', 'POST'])
def complete_appointment():
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash("You must be logged in as a doctor to access this page.", "danger")
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    if not doctor:
        flash("Doctor account not found for current user.", "danger")
        return redirect(url_for('login'))
    if request.method == 'POST':
        appointment_id = request.form.get('appointment_id')
        status = request.form.get('status')
        notes = request.form.get('notes', '')
        if not appointment_id:
            flash("Invalid request. Missing appointment id.", "danger")
            return redirect(url_for('doctor_dashboard'))
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            flash("Appointment not found.", "danger")
            return redirect(url_for('doctor_dashboard'))
        if appointment.doctor_id != doctor.id:
            flash("You are not authorized to update this appointment.", "danger")
            return redirect(url_for('doctor_dashboard'))
        if not status:
            status = 'completed'
        try:
            appointment.status = status
            appointment.notes = notes.strip() or None
            if status == 'completed': 
                appointment.completed_at = datetime.now()
            db.session.commit()
            flash("Appointment updated successfully.", "success")
            return redirect(url_for('doctor_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating appointment. Please try again. ({str(e)})", "danger")
            return redirect(url_for('doctor_dashboard'))
    appointment_id = request.args.get('appointment_id')
    if not appointment_id:
        flash("No appointment selected.", "warning")
        return redirect(url_for('doctor_dashboard'))
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for('doctor_dashboard'))
    if appointment.doctor_id != doctor.id:
        flash("You are not authorized to view this appointmenr.", "danger")
        return redirect(url_for('doctor_dashboard'))

    return render_template('complete_appointment.html', appointment=appointment)
@app.route('/doctor/view_patient_history')
def doctor_view_patient_history():
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash("You must be logged in as a doctor to access this page.", "danger")
        return redirect(url_for('login'))
    patient_id = request.args.get('patient_id')
    if not patient_id:
        flash('No patient selected.', 'warning')
        return redirect(url_for('doctor_dashboard'))
    patient = Patient.query.get(patient_id)
    if not patient:
        flash('Patient not found.', 'danger')
        return redirect(url_for('doctor_dashboard'))
    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    if not doctor:
        flash('Doctor profile not found.', 'danger')
        return redirect(url_for('login'))
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(
        Appointment.date, Appointment.time
    ).all()
    return render_template('view_patient_history.html', patient=patient, appointments=appointments)
@app.route('/doctor/availability', methods=['GET', "POST"])
def doctor_availability():
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash("You must be logged in as a doctor to access this page.", "danger")
        return redirect(url_for('login'))
    if request.method == 'POST':
        date_str = request.form.get('date', '').strip()
        start_str = request.form.get('start_time', '').strip()
        end_str = request.form.get('end_time', '').strip()
        if not date_str or not start_str or not end_str:
            flash("Please provide date, start time and end time.", "warning")
            return redirect(url_for('doctor_availability'))
        
        try:
            av_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", "danger")
            return redirect(url_for('doctor_availability'))
        try:
            av_start = datetime.strptime(start_str, '%H:%M').time()
            av_end = datetime.strptime(end_str, '%H:%M').time()
        except ValueError:
            flash("Invalid time format. Use HH:MM (24-hour).", "danger")
            return redirect(url_for('doctor_availability'))
        start_dt = datetime.combine(av_date, av_start)
        end_dt = datetime.combine(av_date, av_end)
        if end_dt <= start_dt:
            flash("End time must be after start time.", "danger")
            return redirect(url_for('doctor_availability'))
        try:
            doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
            if not doctor:
                flash("Doctor profile not found.", "danger")
                return redirect(url_for('login'))
            availability = Availability(
                doctor_id=doctor.id,
                date=av_date,
                start_time=av_start,
                end_time=av_end,
                created_at=datetime.utcnow()
            )
            db.session.add(availability)
            db.session.commit()
            flash("Availability added successfully", "success")
            return redirect(url_for('doctor_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash("Failed to save availability. Please try again.", "danger")
            return redirect(url_for('doctor_availability'))
    return render_template('doctor_availability.html')

#---------
#PT.ROUTES
#---------
@app.route('/patient/dashboard')
def patient_dashboard():
    if 'user_id' not in session or session.get('role') != 'patient':
        flash('Patient access required.', 'danger')
        return redirect(url_for('login'))
    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    if not patient:
        flash('Patient profile not found.', 'danger')
        return redirect(url_for('login'))
    today = date.today()
    appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.date >= today
    ).order_by(Appointment.date, Appointment.time).all()

    return render_template('patient_dashboard.html', patient=patient, appointments=appointments)
@app.route('/patient/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to book an appointment.", "warning")
        return redirect(url_for('login'))
    #ensure logged in has patient profile...
    patient = Patient.query.filter_by(user_id=user_id).first()
    if not patient:
        flash("No patient profile found for this account.", "danger")
        return redirect(url_for('home'))
    #Get - render form
    if request.method == 'GET':
        doctors = Doctor.query.all()
        return render_template('book_appointment.html', doctors=doctors, patient=patient)
    #Post - handle booking
    doctor_id = request.form.get('doctor_id')
    date_str = request.form.get('date')
    time_str = request.form.get('time')
    reason = (request.form.get('reason') or "").strip()

    if not doctor_id or not date_str or not time_str:
        flash("Please select a doctor and provide date & time.", "danger")
        return redirect(url_for('book_appointment'))
    try:
        doctor_id_int = int(doctor_id)
    except (TypeError, ValueError):
        flash("Invalid doctor selection.", "danger")
        return redirect(url_for('book_appointment'))
    doctor = Doctor.query.get(doctor_id_int)
    if not doctor:
        flash("Selected doctor not found.", "danger")
        return redirect(url_for('book_appointment'))
    #parse date/time
    try:
        appt_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid date format. Use YYYY-MM-DD.", "danger")
        return redirect(url_for('book_appointment'))
    try:
        appt_time = datetime.strptime(time_str, '%H:%M').time()
    except ValueError:
        flash("Invalid time format. Use HH:MM.", "danger")
        return redirect(url_for('book_appointment'))
    #conflict check 
    conflict = Appointment.query.filter_by(
        doctor_id=doctor.id,
        date=appt_date,
        time=appt_time
    ).first()
    if conflict:
        flash("Selected doctor already has an appointment at that date & time.", "warning")
        return redirect(url_for('book_appointment'))
    #create and save appt
    new_appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        date=appt_date,
        time=appt_time,
        reason=reason,
        status='pending'
    )
    try:
        db.session.add(new_appt)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("Could not create appointment. Try again.", "danger")
        return redirect(url_for('book_appointment'))
    flash("Appointment booked successfully.", "success")
    return redirect(url_for('patient_dashboard'))
@app.route('/patient/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    if 'user_id' not in session or session.get('role') != 'patient':
        flash('Patient access required.', 'danger')
        return redirect(url_for('login'))
    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    if not patient:
        flash('Patient account not found.', 'danger')
        return redirect(url_for('patient_dashboard'))
    
    appt = Appointment.query.get(appointment_id)
    if not appt:
        flash("Appointment not found.", "danger")
        return redirect(url_for('patient_dashboard'))
    
    if appt.patient_id != patient.id:
        flash("You cannot cancel someone else's appointment.", "danger")
        return redirect(url_for('patient_dashboard'))
    current_status = (appt.status or "").strip().lower()
    if current_status != "pending":
        flash(f"Only pending appointments can be cancelled. Current status: {appt.status}", "warning")
        return redirect(url_for('patient_dashboard'))
    try:
        appt.status = "cancelled"
        db.session.commit()
        flash("Appointment cancelled successfully.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Failed to cancel appointment")
        flash(f"Error cancelling appointment: {str(e)}", "danger")
    return redirect(url_for('appointment_history'))

@app.route('/patient/appointment_history')
def patient_appointment_history():
    if 'user_id' not in session or session.get('role') != 'patient':
        flash('Patient access required.', 'danger')
        return redirect(url_for('login'))
    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    if not patient:
        flash('Patient profile not found.', 'danger')
        return redirect(url_for('login'))
    appointments = Appointment.query.filter_by(
        patient_id=patient.id
    ).order_by(Appointment.date, Appointment.time).all()
    return render_template('view_patient_history.html', patient=patient, appointments=appointments)

#-------
#DB init
#-------
if not os.path.exists( os.path.join(BASE_DIR, 'instance')):
    os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
    
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        pass

#------------
#Server Run..
#------------
if __name__ == "__main__":
    app.secret_key = "demo@1920"
    app.run(host="0.0.0.0", port=5000, debug=True)