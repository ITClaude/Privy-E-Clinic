import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime

# --- DATABASE MODULE ---
def init_db():
    conn = sqlite3.connect('privy_eclinic.db', check_same_thread=False)
    c = conn.cursor()
    # Core Tables based on Proposal: Auth, Appointments, Prescriptions, Messaging [cite: 45]
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS providers 
                 (id INTEGER PRIMARY KEY, name TEXT, bio TEXT, image_url TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS appointments 
                 (id INTEGER PRIMARY KEY, patient_name TEXT, provider_name TEXT, date TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (id INTEGER PRIMARY KEY, sender TEXT, receiver TEXT, content TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS prescriptions 
                 (id INTEGER PRIMARY KEY, patient_name TEXT, provider_name TEXT, medication TEXT, instructions TEXT, date TEXT)''')
    
    # Pre-populate Providers [cite: 3, 13]
    c.execute("SELECT COUNT(*) FROM providers")
    if c.fetchone()[0] == 0:
        providers = [
            ("RN NSHUMBUSHO Jean De Dieu", "Registered Nurse (8+ yrs). Expert in primary healthcare & inclusion.", "https://cdn-icons-png.flaticon.com/512/387/387561.png"),
            ("RN Mahoro Florance", "Registered Nurse (5 yrs). Specialist in reproductive health & inclusion.", "https://cdn-icons-png.flaticon.com/512/387/387569.png")
        ]
        c.executemany("INSERT INTO providers (name, bio, image_url) VALUES (?, ?, ?)", providers)
    conn.commit()
    return conn

conn = init_db()

# --- SECURITY & STYLING ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text: return hashed_text
    return False

def local_css():
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.85)), 
            url("https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=1350&q=80");
            background-size: cover;
        }
        .card { 
            padding: 20px; border-radius: 15px; background: rgba(255, 255, 255, 0.98); 
            box-shadow: 0 8px 20px rgba(0,0,0,0.12); margin-bottom: 15px;
            border-left: 6px solid #2D5A27;
        }
        .welcome-box { 
            background: linear-gradient(135deg, #1a3a5f 0%, #2D5A27 100%); 
            color: white; padding: 35px; border-radius: 20px; margin-bottom: 25px; text-align: center;
        }
        .msg-bubble { padding: 12px; border-radius: 12px; margin: 8px 0; font-size: 14px; }
        .sent { background-color: #e3f2fd; border-right: 5px solid #1e88e5; text-align: right; }
        .received { background-color: #f1f8e9; border-left: 5px solid #43a047; text-align: left; }
        </style>
    """, unsafe_allow_html=True)

# --- MESSAGING MODULE ---
def show_chat_history(user):
    st.markdown("### 📩 Secure Messaging History")
    query = "SELECT sender, receiver, content, timestamp FROM messages WHERE sender = ? OR receiver = ? ORDER BY id DESC"
    msgs = conn.execute(query, (user, user)).fetchall()
    
    if not msgs:
        st.info("Your secure inbox is currently empty.")
    else:
        for m in msgs:
            sender, receiver, content, time = m
            msg_class = "sent" if sender == user else "received"
            label = f"To: {receiver}" if sender == user else f"From: {sender}"
            st.markdown(f'<div class="msg-bubble {msg_class}"><b>{label}</b><br>{content}<br><small>{time}</small></div>', unsafe_allow_html=True)

# --- DASHBOARDS ---
def patient_dashboard():
    st.markdown(f"## Welcome to your private care space, {st.session_state['username']} ✨")
    st.info("Welcome to Privy E-Clinic Connect (PEC) — your safe, private space for care. Here, you are respected and free to be yourself. Our compassionate healthcare providers are here to listen, support, and care for you with complete confidentiality and dignity. No matter whom you are or what you’re going through, your health matters.")

    t1, t2, t3, t4 = st.tabs(["🏥 Providers", "📅 Consultations", "💬 Messages", "💊 My Prescriptions"])
    
    with t1:
        providers = conn.execute("SELECT * FROM providers").fetchall()
        for p in providers:
            with st.container():
                st.markdown(f'<div class="card"><h4>👩‍⚕️ {p[1]}</h4><p>{p[2]}</p></div>', unsafe_allow_html=True)
                col1, col2 = st.columns([2,1])
                with col1: d = st.date_input("Requested Date", key=f"date_{p[0]}")
                with col2: 
                    if st.button(f"Request Consultation", key=f"btn_{p[0]}"):
                        conn.execute("INSERT INTO appointments (patient_name, provider_name, date, status) VALUES (?,?,?,?)",
                                   (st.session_state['username'], p[1], str(d), "Pending"))
                        conn.commit()
                        st.success(f"Request sent to {p[1]}!")

    with t2:
        st.subheader("Appointment Status")
        df = pd.read_sql(f"SELECT provider_name as Provider, date as Date, status as Status FROM appointments WHERE patient_name='{st.session_state['username']}'", conn)
        st.dataframe(df, use_container_width=True)

    with t3:
        st.subheader("Send Secure Message")
        target = st.selectbox("Choose Provider", [p[1] for p in providers])
        txt = st.text_area("Type your message securely...", height=100)
        if st.button("Send to Provider"):
            if txt.strip():
                conn.execute("INSERT INTO messages (sender, receiver, content, timestamp) VALUES (?,?,?,?)",
                           (st.session_state['username'], target, txt, datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn.commit(); st.success("Sent!"); st.rerun()
        st.divider()
        show_chat_history(st.session_state['username'])

    with t4:
        st.subheader("Your E-Prescriptions")
        presc_df = pd.read_sql(f"SELECT medication as Medication, instructions as Instructions, provider_name as Prescribed_By, date as Date FROM prescriptions WHERE patient_name='{st.session_state['username']}'", conn)
        if presc_df.empty: st.info("No prescriptions found.")
        else: st.dataframe(presc_df, use_container_width=True)

def provider_dashboard():
    st.markdown(f"## Provider Portal: {st.session_state['username']}")
    t1, t2, t3 = st.tabs(["📝 Consultations", "💬 Patient Chat", "💊 Issue Prescription"])
    
    with t1:
        st.subheader("Consultation Requests")
        apps = conn.execute("SELECT id, patient_name, date, status FROM appointments WHERE provider_name LIKE ?", (f"%{st.session_state['username']}%",)).fetchall()
        for a in apps:
            with st.expander(f"Patient: {a[1]} | Requested: {a[2]} | Status: {a[3]}"):
                c1, c2 = st.columns(2)
                if c1.button("Approve Consultation", key=f"app_{a[0]}"):
                    conn.execute("UPDATE appointments SET status='Approved' WHERE id=?", (a[0],))
                    conn.commit(); st.rerun()
                if c2.button("Mark: Completed", key=f"done_{a[0]}"):
                    conn.execute("UPDATE appointments SET status='Consultation Done' WHERE id=?", (a[0],))
                    conn.commit(); st.rerun()

    with t2:
        st.subheader("Message Patient")
        patients = [r[0] for r in conn.execute("SELECT DISTINCT patient_name FROM appointments WHERE provider_name LIKE ?", (f"%{st.session_state['username']}%",)).fetchall()]
        reply_to = st.selectbox("Select Patient", patients if patients else ["No patients assigned"])
        reply_txt = st.text_area("Clinical Response")
        if st.button("Send Reply"):
            if reply_to != "No patients assigned" and reply_txt.strip():
                conn.execute("INSERT INTO messages (sender, receiver, content, timestamp) VALUES (?,?,?,?)",
                           (st.session_state['username'], reply_to, reply_txt, datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn.commit(); st.success(f"Reply sent to {reply_to}!"); st.rerun()
        st.divider()
        show_chat_history(st.session_state['username'])

    with t3:
        st.subheader("Issue Digital Prescription")
        target_p = st.selectbox("Patient Name", patients if patients else ["No patients assigned"], key="presc_p")
        meds = st.text_input("Medication Name")
        instr = st.text_area("Dosage & Instructions")
        if st.button("Issue Prescription"):
            if target_p != "No patients assigned":
                conn.execute("INSERT INTO prescriptions (patient_name, provider_name, medication, instructions, date) VALUES (?,?,?,?,?)",
                           (target_p, st.session_state['username'], meds, instr, datetime.now().strftime("%Y-%m-%d")))
                conn.commit(); st.success(f"Prescription issued for {target_p}!")

# --- AUTH FLOW ---
def main():
    local_css()
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
    
    if not st.session_state['logged_in']:
        st.markdown('<div class="welcome-box"><h1>Privy E-Clinic Connect</h1><p>Confidential & Stigma-Free Healthcare Access</p></div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Secure Login")
            u, p = st.text_input("Username"), st.text_input("Password", type='password')
            if st.button("Access Platform"):
                data = conn.execute('SELECT password, role FROM users WHERE username = ?', (u,)).fetchone()
                if data and check_hashes(p, data[0]):
                    st.session_state.update({'logged_in': True, 'username': u, 'role': data[1]})
                    st.rerun()
                else: st.error("Access denied. Please check your credentials.")
        with col2:
            st.subheader("Anonymous Registration")
            nu, np = st.text_input("New Username"), st.text_input("New Password", type='password')
            nr = st.selectbox("Account Type", ["Patient", "Healthcare Provider"])
            if st.button("Create Account"):
                try:
                    conn.execute('INSERT INTO users(username, password, role) VALUES (?,?,?)', (nu, make_hashes(np), nr))
                    conn.commit(); st.success("Welcome! You can now log in.")
                except: st.warning("Username is already taken.")
    else:
        st.sidebar.title("PEC Navigation")
        if st.sidebar.button("Log Out"): 
            st.session_state['logged_in'] = False
            st.rerun()
        
        if st.session_state['role'] == "Patient": patient_dashboard()
        else: provider_dashboard()

if __name__ == '__main__': main()