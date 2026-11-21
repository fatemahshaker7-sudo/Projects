import smtplib
import time
from datetime import datetime
from email.message import EmailMessage
import cv2
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer
from face_helper_fun import (S, ATTENDANCE_PATH, LOG_PATH, LOG_COLUMNS, PROCESS_SIZE, snapshot, save_pickle, save_students, shrink, detect_faces, get_embedding, check_left, attendance_table, load_log, video_callback)

st.set_page_config(page_title="Class Mind", layout="wide")

# Email settings
EMAIL_EVENTS = ["Arrived", "Left class"]   # add "Returned" to email those too
EMAILS_PER_REFRESH = 3                     # keeps the page responsive if many students arrive at once
SERVERS = {"gmail.com": ("smtp.gmail.com", 465), "outlook.com": ("smtp-mail.outlook.com", 587), "hotmail.com": ("smtp-mail.outlook.com", 587)}
EMB_COLS = [f"e{i}" for i in range(128)]
BACKUP_COLS = ["Student", "Parent_email"] + EMB_COLS

@st.fragment(run_every=2)
def live_view():
    """Refreshes by itself every 2 seconds without restarting the camera, and sends the parent emails."""
    today = datetime.now().strftime("%Y-%m-%d")
    mail, sent = S["settings"]["mail"], 0

    # email parents about new arrivals / departures (sent here, so the video never waits for mail)
    for name, s in list(S["att"].get(today, {}).items()):
        s.setdefault("emailed", len(s["events"]))            # old records: existing events count as handled
        while s["emailed"] < len(s["events"]):
            when, event = s["events"][s["emailed"]]
            emailable = event in EMAIL_EVENTS and mail["on"]
            if emailable and sent == EMAILS_PER_REFRESH:
                break                                         # the rest go out on the next refresh
            s["emailed"] += 1                                 # marked as handled first, so a failed email is never retried forever
            if not emailable:
                continue
            sent += 1
            to_addr, domain = S["parents"].get(name), mail["sender"].split("@")[-1].lower()
            if not to_addr or domain not in SERVERS:
                S["email_log"].append(f"{datetime.now():%H:%M:%S}  skipped {name}: no parent email saved, " "or the sender is not a Gmail / Outlook / Hotmail address")
                continue
            subject = f"{name} arrived at class" if event == "Arrived" else f"{name} left class"
            text = (f"{name} arrived in class on {when[:10]} at {when[11:]}." if event == "Arrived" else
                    f"{name} left class on {when[:10]}. {name} was last seen in class at {when[11:]}.")
            host, port = SERVERS[domain]
            msg = EmailMessage()
            msg["From"], msg["To"], msg["Subject"] = mail["sender"], to_addr, subject
            msg.set_content(f"Dear parent,\n\n{text}\n\nThis is an automated message from Class Mind.")
            with (smtplib.SMTP_SSL(host, port, timeout=20) if port == 465 else smtplib.SMTP(host, port, timeout=20)) as server:
                if port != 465:
                    server.starttls()
                server.login(mail["sender"], mail["password"])
                server.send_message(msg)
            S["email_log"].append(f"{datetime.now():%H:%M:%S}  sent to {to_addr}: {subject}")

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

# sidebar
page = st.sidebar.radio("Page", ["Class", "Enroll"])
gone_secs = st.sidebar.number_input("Mark as 'left class' after (seconds not seen)", 10, 1800, 60)
debug = st.sidebar.checkbox("Show debug values")
sender = st.sidebar.text_input("Sender email (for parent notifications)").strip()
password = st.sidebar.text_input("Sender password", type="password")
S["settings"] = {"gone_secs": int(gone_secs), "debug": debug, "mail": {"on": bool(sender and password), "sender": sender, "password": password}}

if page == "Enroll":
    st.header("Enroll students")
    name = st.text_input("Student name").strip()
    email = st.text_input("Parent email").strip()
    valid_email = "@" in email and "." in email.split("@")[-1]
    if email and not valid_email:
        st.caption("Please enter a valid email address.")

    tab1, tab2 = st.tabs(["Take photo", "Upload photos"])
    shot = tab1.camera_input("Clear, front-facing photo")
    files = tab2.file_uploader("Upload photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    uploads = ([shot] if shot else []) + list(files or [])
    images = [shrink(img, 1280) for img in (cv2.imdecode(np.frombuffer(f.getvalue(), np.uint8), cv2.IMREAD_COLOR) for f in uploads) if img is not None]

    if st.button("Enroll", disabled=not (name and valid_email and images)):
        added = 0
        for img in images:
            faces = detect_faces(img)
            if len(faces) > 0:
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
        col1, col2 = st.columns([4, 1])
        col1.write(f"{student} ({len(embs)} photos) - {S['parents'].get(student, 'no parent email')}")
        if col2.button("Remove", key=f"remove_{student}"):
            S["db"].pop(student, None)
            S["parents"].pop(student, None)
            save_students()
            st.rerun()

else:   # monitoring and report share one page so the camera keeps running while you read the report
    tab_live, tab_report = st.tabs(["Live monitoring", "Report"])

    with tab_live:
        if not S["db"]:
            st.warning("Enroll at least one student first.")
        else:
            st.write("Press START, allow camera access, and keep this page open while class is in session. " "Use one browser tab with one camera at a time.")
            webrtc_streamer( key="classroom",
                mode=WebRtcMode.SENDRECV,
                rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
                media_stream_constraints={"video": {"width": {"ideal": PROCESS_SIZE}, "height": {"ideal": int(PROCESS_SIZE * 0.75)}, "frameRate": {"ideal": 15}}, "audio": False},
                video_frame_callback=video_callback, async_processing=True)
            live_view()

    with tab_report:
        att, names, log = snapshot(S["att"]), list(S["db"]), load_log()
        check_left(att, time.time(), gone_secs)   # on a copy, only for display
        day = st.date_input("Date", value=datetime.now().date()).strftime("%Y-%m-%d")
        day_log = log[log["Date"] == day]
        tab1, tab2, tab3 = st.tabs(["Attendance", "Attention", "Log file"])

        with tab1:
            table = attendance_table(att, day, names)
            if table.empty:
                st.info("No students enrolled and no attendance recorded for this date.")
            else:
                st.subheader(f"Class attendance on {day}")
                st.dataframe(table, hide_index=True)

            event_rows = [{"Student": n, "Time": t, "Event": e} for n, s in att.get(day, {}).items() for t, e in s["events"]]
            if event_rows:
                with st.expander("Arrivals, departures and returns"):
                    st.dataframe(pd.DataFrame(event_rows).sort_values("Time"), hide_index=True)

            totals = {}
            for students in att.values():
                for n, s in students.items():
                    days, secs = totals.get(n, (0, 0))
                    totals[n] = (days + 1, secs + s["present_secs"])
            if totals:
                with st.expander("Total hours across all days"):
                    st.dataframe(pd.DataFrame([{"Student": n, "Days attended": d, "Total hours": round(secs / 3600, 2)}  for n, (d, secs) in totals.items()]), hide_index=True)

        with tab2:
            rows = []
            for n, g in day_log.groupby("Student"):
                counts, visible = g["Attention"].value_counts(), int((g["Visible"] == 1).sum())
                row = {"Student": n, "Attention %": round(100 * counts.get("Attentive", 0) / visible, 1) if visible else 0.0}
                row.update({f"{k} (s)": int(counts.get(k, 0)) for k in ["Attentive", "Looking away", "Side-talking",  "Head down", "Sleepy", "Not visible"]})
                rows.append(row)
            if not rows:
                st.info("No attention data recorded for this date.")
            else:
                st.subheader(f"Attention on {day}")
                st.dataframe(pd.DataFrame(rows), hide_index=True)

        with tab3:
            if day_log.empty:
                st.info("No log rows for this date.")
            else:
                st.caption(f"{len(day_log)} rows on {day} (showing the last 500)")
                st.dataframe(day_log.tail(500), hide_index=True)

            # full log: per-second rows + arrival/left/returned events + absent students, with first/last seen of each day
            pairs = [(d, n, s) for d, students in att.items() for n, s in students.items()]
            summary = pd.DataFrame([{"Date": d, "Student": n, "First_seen": s["first_seen"], "Last_seen_of_day": s["last_seen"]} for d, n, s in pairs], columns=["Date", "Student", "First_seen", "Last_seen_of_day"])
            event_log = pd.DataFrame([{"Date": d, "Time": t[11:], "Student": n, "Event": e, "Status": "Left class" if e == "Left class" else "In class"} for d, n, s in pairs for t, e in s["events"]])
            absent = pd.DataFrame([{"Date": d, "Student": n, "Status": "Absent", "Visible": 0, "Attention": "Absent", "Time_in_class_secs": 0, "Time_away_secs": 0, "Times_left": 0} for d, students in att.items() for n in names if n not in students])
            cols = LOG_COLUMNS + ["Event", "First_seen", "Last_seen_of_day"]
            parts = [p for p in (log.assign(Event=""), event_log, absent) if not p.empty]
            if parts:
                full = pd.concat(parts, ignore_index=True).merge(summary, on=["Date", "Student"], how="left")
                for col in ["Visible", "Time_in_class_secs", "Time_away_secs", "Times_left"]:
                    full[col] = pd.to_numeric(full[col], errors="coerce").astype("Int64")   # whole numbers, no 1.0
                full = full.sort_values(["Date", "Time", "Student"])[cols]
            else:
                full = pd.DataFrame(columns=cols)

            st.download_button("Download full log (CSV)", full.to_csv(index=False), "class_log_full.csv", disabled=full.empty)
            st.caption("On a cloud server the log is temporary: download it at the end of each day.")
            if st.button("Clear all data for this date"):
                S["att"].pop(day, None)
                save_pickle(ATTENDANCE_PATH, S["att"])
                remaining = load_log()
                if not remaining.empty:
                    remaining[remaining["Date"] != day].to_csv(LOG_PATH, index=False)
                st.rerun()
