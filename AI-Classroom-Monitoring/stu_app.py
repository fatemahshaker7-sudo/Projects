import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import smtplib, time
from datetime import datetime
from email.message import EmailMessage
import cv2, numpy as np, pandas as pd, streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer
from style import apply_style
from face_helper_fun import (S, ATTENDANCE_PATH, LOG_PATH, LOG_COLUMNS, PROCESS_SIZE, snapshot, save_pickle, save_students, shrink, detect_faces, get_embedding, check_left, attendance_table, load_log, video_callback, bahrain_time)

st.set_page_config(page_title="Class Mind", layout="wide")
apply_style()
EMAIL_EVENTS = ["Arrived", "Left class"]
EMAILS_PER_REFRESH = 3
SERVERS = {"gmail.com": ("smtp.gmail.com", 465), "outlook.com": ("smtp-mail.outlook.com", 587), "hotmail.com": ("smtp-mail.outlook.com", 587)}
EMB_COLS = [f"e{i}" for i in range(128)]
BACKUP_COLS = ["Student", "Parent_email"] + EMB_COLS

@st.fragment(run_every=2)
def live_view():
    today, mail, sent = bahrain_time().strftime("%Y-%m-%d"), S["settings"]["mail"], 0
    for name, s in list(S["att"].get(today, {}).items()):
        s.setdefault("emailed", len(s["events"]))
        while s["emailed"] < len(s["events"]):
            when, event = s["events"][s["emailed"]]
            emailable = event in EMAIL_EVENTS and mail["on"]
            if emailable and sent == EMAILS_PER_REFRESH:
                break
            s["emailed"] += 1
            if not emailable:
                continue
            sent += 1
            to_addr, domain = S["parents"].get(name), mail["sender"].split("@")[-1].lower()
            if not to_addr or domain not in SERVERS:
                S["email_log"].append(f"{bahrain_time():%H:%M:%S}  skipped {name}: no parent email saved, or sender is not a Gmail / Outlook / Hotmail address")
                continue
            subject = f"{name} arrived at class" if event == "Arrived" else f"{name} left class"
            text = f"{name} arrived in class on {when[:10]} at {when[11:]}." if event == "Arrived" else f"{name} left class on {when[:10]}. {name} was last seen in class at {when[11:]}"
            host, port = SERVERS[domain]
            msg = EmailMessage()
            msg["From"], msg["To"], msg["Subject"] = mail["sender"], to_addr, subject
            msg.set_content(f"Dear parent,\n\n{text}\n\nThis is an automated message from Class Mind.")
            with (smtplib.SMTP_SSL(host, port, timeout=20) if port == 465 else smtplib.SMTP(host, port, timeout=20)) as server:
                if port != 465:
                    server.starttls()
                server.login(mail["sender"], mail["password"])
                server.send_message(msg)
            S["email_log"].append(f"{bahrain_time():%H:%M:%S}  sent to {to_addr}: {subject}")
    age = time.time() - S["last_process"] if S["last_process"] else None
    if age is None:
        st.info("Waiting for the camera. Press START above.")
    elif age < 5:
        st.success("Camera is connected and students are being tracked.")
    else:
        st.info("No camera frames received in the last few seconds.")
    st.subheader("Today's attendance")
    st.dataframe(attendance_table(snapshot(S["att"]), today, list(S["db"])), hide_index=True)
    if mail["on"]:
        st.text("\n".join(S["email_log"][-5:]) or "No emails sent yet.")

page = st.sidebar.radio("Page", ["Class", "Enroll", "Dashboard"])
gone_secs = st.sidebar.number_input("Mark as 'left class' after (seconds not seen)", 10, 1800, 60)
sender = st.sidebar.text_input("Sender email (for parent notifications)").strip()
password = st.sidebar.text_input("Sender password", type="password")
S["settings"] = {"gone_secs": int(gone_secs), "mail": {"on": bool(sender and password), "sender": sender, "password": password}}

if page == "Enroll":
    st.header("Enroll students")
    name, email = st.text_input("Student name").strip(), st.text_input("Parent email").strip()
    valid_email = "@" in email and "." in email.split("@")[-1]
    if email and not valid_email:
        st.caption("Please enter a valid email address.")
    tab1, tab2 = st.tabs(["Take photo", "Upload photos"])
    shot, files = tab1.camera_input("Clear, front-facing photo"), tab2.file_uploader("Upload photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    uploads = ([shot] if shot else []) + list(files or [])
    images = [shrink(img, 1280) for img in (cv2.imdecode(np.frombuffer(f.getvalue(), np.uint8), cv2.IMREAD_COLOR) for f in uploads) if img is not None]
    if st.button("Enroll", disabled=not (name and valid_email and images)):
        added = 0
        for img in images:
            faces = detect_faces(img)
            if faces:
                S["db"].setdefault(name, []).append(get_embedding(img, max(faces, key=lambda f: f[2] * f[3])))
                added += 1
        if added < len(images):
            st.warning(f"No face found in {len(images) - added} photo(s), skipped.")
        if added:
            S["parents"][name] = email
            save_students()
            st.success(f"Saved {name} (parent: {email})")
    st.subheader("Enrolled students")
    for student, embs in list(S["db"].items()):
