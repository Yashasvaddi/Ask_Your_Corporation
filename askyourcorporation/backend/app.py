from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
from typing import Optional
from twilio.rest import Client

load_dotenv()

cursor=None
conn=None

app=FastAPI()

def login():
    global cursor,conn
    try:
        conn=mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="XXXX",
        database="XXXX"
    )

        cursor=conn.cursor()
        print("Connection to DB successfull")

    except mysql.connector.Error as e:
        print("Error: ", e)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # or ["http://127.0.0.1:5501"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class login_info_in(BaseModel):
    uuid: str
    name: str
    aadhar_no: str
    phone_no: str
    ward_no: str
    type: int
    officer_id: Optional[str] = None 

def disp_table(table_name):
    global cursor,conn
    query = f"SELECT * FROM {table_name};"
    cursor.execute(query)
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    print("Updated DB!")

@app.post('/ayc/login')
def login_info(payload: login_info_in):
    login()
    global cursor,conn

    if cursor is None or conn is None or not conn.is_connected():
        login()

    if payload.type==0:
        insert_query = """
            INSERT INTO login_info(uuid, name, aadhar_no, phone_no, ward_no, user_type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        data = (
            payload.uuid,
            payload.name,
            payload.aadhar_no.encode(),  # convert string to bytes for varbinary
            payload.phone_no,
            payload.ward_no,
            payload.type
        )
        cursor.execute(insert_query, data)
        conn.commit()
	

    else:
        insert_query = """
            INSERT INTO officer_info(uuid, name, aadhar_no, phone_no, ward_no, user_type, officer_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """    
        data = (
            payload.uuid,
            payload.name,
            payload.aadhar_no.encode(),  # convert string to bytes for varbinary
            payload.phone_no,
            payload.ward_no,
            payload.type,
            payload.officer_id
        )
        cursor.execute(insert_query, data)
        conn.commit()

    print("Data inserted into db")
    return payload


class complaint_info(BaseModel):
    complaint_uuid:str
    user_uuid:str
    lat:str
    long:str
    date:str
    mssg:str
    base_64:str
    ward_no:str

@app.post('/ayc/complaint')
def complaint(payload: complaint_info):
    global conn, cursor

    if cursor is None or conn is None or not conn.is_connected():
        login()

    insert_complaint = """
        INSERT INTO complaint_info(complaint_uuid, user_uuid, lat, lon, date, mssg, base_64, ward_no)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    data = (
        payload.complaint_uuid,
        payload.user_uuid,
        payload.lat,
        payload.long,
        payload.date,
        payload.mssg,
        payload.base_64,
        payload.ward_no
    )

    cursor.execute(insert_complaint, data)
    conn.commit()
    print("Complaint inserted into DB")
    
    return payload



class fetchcomplaints(BaseModel):
    member_uuid:str

@app.post('/ayc/fetchcomplaint')
def fetchcomplaint(payload: fetchcomplaints):
    global conn, cursor

    if cursor is None or conn is None or not conn.is_connected():
        login()
    
    query = """
        select c.complaint_uuid, c.user_uuid, c.lat, c.lon, c.date, c.mssg, c.base_64, c.ward_no 
        from complaint_info c
        join officer_info o on o.ward_no = c.ward_no;
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    # Convert SQL rows to JSON format that matches frontend expectations
    complaints = []
    for row in rows:
        complaints.append({
            "uuid": row[0],       # complaint_uuid
            "user_uuid": row[1],
            "lat": row[2],
            "long": row[3],
            "date": row[4],
            "mssg": row[5],
            "base_64": row[6],
            "ward_no": row[7]
        })
    conn.commit()
    return complaints

class resolve_info(BaseModel):
    complaint_id:str
    base_64:str
    date:str
    mssg:str


@app.post("/ayc/resolve")
def response(payload: resolve_info):
    global conn, cursor

    if cursor is None or conn is None or not conn.is_connected():
        login()

    # fetch phone number
    cursor.execute("""
        SELECT l.phone_no 
        FROM login_info l
        JOIN complaint_info c ON c.user_uuid = l.uuid
        WHERE c.complaint_uuid = %s
    """, (payload.complaint_id,))
    row = cursor.fetchone()

    if not row:
        return {"status": "failed", "message": "User not found"}

    phone_no = row[0]

    print(phone_no)

    # Twilio — send message only
    account_sid = 'XXX'
    auth_token = 'XXX'
    client = Client(account_sid, auth_token)

    message = client.messages.create(
    from_="whatsapp:XXXXX",  # Twilio sandbox number
    body="XXX",
    to=f"whatsapp:+91{phone_no}"     # replace with your phone
)
    conn.commit()
    return {
        "status": "success",
        "complaint_id": payload.complaint_id,
        "phone_no": phone_no,
        "whatsapp_sid": message.sid
    }
