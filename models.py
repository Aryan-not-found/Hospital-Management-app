from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    """
    Authentication user table, role: 'admin', 'doctor', or 'patient'
    Passwords stored hashed.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="patient")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    # Relationships..
    doctor = db.relationship("Doctor", backref="user",uselist=False, cascade="all, delete")
    patient = db.relationship("Patient", backref="user",uselist=False, cascade="all, delete")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f"<User {self.id} {self.email} ({self.role})>"
    
class Doctor(db.Model):



    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    specialization = db.Column(db.String(120), nullable=True)
    contact = db.Column(db.String(50), nullable=True)
    #availability can be stored as JSON/text or separate table; keep simple:
    availability = db.Column(db.Text, nullable=True)

    #Appointments provided by this doctor
    appointments = db.relationship("Appointment", backref="doctor", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Doctor {self.id} user_id={self.user_id} spec={self.specialization}>"

class Patient(db.Model):



    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    contact = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=True)
    #optional
    notes = db.Column(db.Text, nullable=True)
    #Appointment req from patients
    appointments = db.relationship("Appointment", backref="patient", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Patient {self.id} user_id={self.user_id}>"

class Appointment(db.Model):



    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=True)
    reason = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), nullable=False, default="pending") #pending , completed , cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def mark_completed(self):
        self.status = "completed"
        self.completed_at = datetime.utcnow()

    @property
    def patient_name(self):

        if self.patient and self.patient.user:
            return self.patient.user.name
        return None
        
    @property
    def doctor_name(self):
        if self.doctor and self.doctor.user:
            return self.doctor.user.name
        return None
        
    def __repr__(self):
        return f"<Appointment {self.id} patient_id={self.patient_id} doctor_id={self.doctor_id} date={self.date} status={self.status}>"
    
class Availability(db.Model):
    __tablename__ = "availabilities"
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doctor = db.relationship("Doctor", backref=db.backref("availabilities", lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<Availability {self.id} doctor_id={self.doctor_id} date={self.date} {self.start_time}-{self.end_time}>"
    