from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import csv
import os
import re
from datetime import datetime

app = FastAPI()

# CSV file path
CSV_FILE = r"D:\POC1(HOSPITAL)\adamrecords.csv"

# Expected CSV Headers
EXPECTED_FIELDS = ["referral_id", "patient_id", "current_department", "referred_department", 
                   "reason", "referred_by", "notes", "timestamp", "specialist_available"]

# Ensure CSV file exists with correct headers
def initialize_csv():
    if not os.path.exists(CSV_FILE) or os.stat(CSV_FILE).st_size == 0:
        with open(CSV_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(EXPECTED_FIELDS)  # Write headers

initialize_csv()

# Function to get the next sequential referral ID
def get_next_referral_id():
    try:
        with open(CSV_FILE, mode='r') as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header
            referrals = list(reader)
            if referrals:
                last_id = int(referrals[-1][0][3:])  # Extract numeric part
                return f"REF{last_id + 1:06d}"
        return "REF000001"
    except Exception:
        return "REF000001"

# Validation functions
def validate_patient_id(patient_id: str) -> bool:
    return bool(re.fullmatch(r"PAT\d{6,}", patient_id))

def validate_doctor_id(doctor_id: str) -> bool:
    return bool(re.fullmatch(r"DOC\d{6,}", doctor_id))

def validate_referral_id(referral_id: str) -> bool:
    return bool(re.fullmatch(r"REF\d{6}", referral_id))

def validate_department(department: str) -> bool:
    valid_departments = {"General Medicine", "Neurology", "Cardiology", "Orthopedics", "Pediatrics",
                         "Dermatology", "Oncology", "Endocrinology", "Gastroenterology"}
    return department in valid_departments

def check_department_availability(department: str) -> bool:
    available_departments = {"Neurology": True, "Cardiology": True, "Orthopedics": False,
                             "Pediatrics": True, "Dermatology": True, "Oncology": False,
                             "Endocrinology": True, "Gastroenterology": True}
    return available_departments.get(department, False)

def notify_department(referral_id: str, department: str):
    return f"Notification sent to {department} for referral ID {referral_id}."

# Pydantic model for referral request
class ReferralRequest(BaseModel):
    patient_id: str
    current_department: str
    referred_department: str
    reason: str
    referred_by: str
    notes: str

# POST: Create Referral Request
@app.post("/referrals/create")
def create_referral(referral: ReferralRequest):
    if not validate_patient_id(referral.patient_id):
        raise HTTPException(status_code=400, detail="Invalid patient ID format.")
    if not validate_doctor_id(referral.referred_by):
        raise HTTPException(status_code=400, detail="Invalid doctor ID format.")
    if not validate_department(referral.current_department) or not validate_department(referral.referred_department):
        raise HTTPException(status_code=400, detail="Invalid department name.")
    
    specialist_available = check_department_availability(referral.referred_department)
    referral_id = get_next_referral_id()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([referral_id, referral.patient_id, referral.current_department, 
                         referral.referred_department, referral.reason, referral.referred_by, 
                         referral.notes, timestamp, specialist_available])
    
    return {
        "message": f"Referral created successfully.",
        "referral_id": referral_id,
        "timestamp": timestamp,
        "notification": notify_department(referral_id, referral.referred_department)
    }

# GET: Retrieve Referral Details
@app.get("/referrals/{referral_id}")
def get_referral(referral_id: str):
    if not validate_referral_id(referral_id):
        raise HTTPException(status_code=400, detail="Invalid referral ID format.")

    if not os.path.exists(CSV_FILE) or os.stat(CSV_FILE).st_size == 0:
        raise HTTPException(status_code=404, detail="Referral database is empty.")
    
    try:
        with open(CSV_FILE, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames or sorted(reader.fieldnames) != sorted(EXPECTED_FIELDS):
                raise HTTPException(status_code=500, detail="CSV structure is invalid.")

            for row in reader:
                if row["referral_id"] == referral_id:
                    return row
        raise HTTPException(status_code=404, detail="Referral not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
