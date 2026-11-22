import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage
import cv2
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer
from style import apply_style
from face_helper_fun import (S, ATTENDANCE_PATH, LOG_PATH, LOG_COLUMNS, PROCESS_SIZE, snapshot, save_pickle, save_students, shrink, detect_faces, get_embedding, check_left, attendance_table, load_log, video_callback, bahrain_time)

st.set_page_config(page_title="Class Mind", layout="wide")

apply_style()

# Email settings
EMAIL_EVENTS = ["Arrived", "Left class"]   # add "Returned" to email those too
EMAILS_PER_REFRESH = 3                     # keeps the page responsive if many students arrive at once
SERVERS = {"gmail.com": ("smtp.gmail.com", 465), "outlook.com": ("smtp-mail.outlook.com", 587), "hotmail.com": ("smtp-mail.outlook.com", 587)}
EMB_COLS = [f"e{i}" for i in range(128)]
BACKUP_COLS = ["Student", "Parent_email"] + EMB_COLS

@st.fragment(run_every=2)
def live_view():
    """Refreshes by itself every 2 seconds without restarting the camera, and sends the parent emails."""
    today = bahrain_time().strftime("%Y-%m-%d")
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
                S["email_log"].append(f"{bahrain_time():%H:%M:%S}  skipped {name}: no parent email saved, " "or the sender is not a Gmail / Outlook / Hotmail address")
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

# sidebar
page = st.sidebar.radio("Page", ["Class", "Enroll", "Dashboard"])
gone_secs = st.sidebar.number_input("Mark as 'left class' after (seconds not seen)", 10, 1800, 60)
sender = st.sidebar.text_input("Sender email (for parent notifications)").strip()
password = st.sidebar.text_input("Sender password", type="password")
S["settings"] = {"gone_secs": int(gone_secs), "mail": {"on": bool(sender and password), "sender": sender, "password": password}}

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
elif page == "Dashboard":
    st.header("Dashboard")
    log = load_log().reindex(columns=LOG_COLUMNS)
    if log.empty:
        st.info("No data yet. Run a monitoring session first.")
        st.stop()

    # filters
    dates, all_students = sorted(log["Date"].unique()), sorted(log["Student"].unique())
    c1, c2 = st.columns(2)
    start = c1.selectbox("From", dates, index=0)
    end = c2.selectbox("To", dates, index=len(dates) - 1)
    students = st.multiselect("Students", all_students, default=all_students)
    data = log[(log["Date"] >= start) & (log["Date"] <= end) & log["Student"].isin(students)]
    if data.empty:
        st.warning("No data for this selection.")
        st.stop()

    # numbers behind the dashboard
    seen = data[data["Visible"] == 1]                                            # seconds when the student was on camera
    class_secs = data.groupby(["Date", "Student"])["Time_in_class_secs"].max()   # running total, so the last value is the day's total
    emo = seen["Emotion"].dropna()
    emo = emo[emo != ""]
    attention = round(100 * (seen["Attention"] == "Attentive").mean(), 1) if len(seen) else 0
    kpis = {"Students": data["Student"].nunique(), "Days": data["Date"].nunique(),
            "Hours in class": round(class_secs.sum() / 3600, 1), "Average attention": f"{attention}%",
            "Times left class": int(data.groupby(["Date", "Student"])["Times_left"].max().sum()),
            "Most common emotion": emo.mode()[0] if len(emo) else "-"}

    STATES = ["Attentive", "Looking away", "Side-talking", "Head down", "Sleepy", "Not visible"]
    STATE_COLORS = ["#6B9080", "#E9B44C", "#D1603D", "#4A6FA5", "#7D5BA6", "#B8C0BC"]

    # each chart is drawn on an axis, so the same drawing is used on the page and in the PDF
    def chart_attention(ax):
        pct = seen.groupby("Student")["Attention"].apply(lambda s: 100 * (s == "Attentive").mean())
        ax.barh(pct.index, pct.values, color="#6B9080")
        ax.set_xlim(0, 100)
        ax.set_xlabel("% of on-camera time attentive")

    def chart_breakdown(ax):
        secs = data.groupby(["Student", "Attention"]).size().unstack(fill_value=0).reindex(columns=STATES, fill_value=0)
        left = np.zeros(len(secs))
        for state, color in zip(STATES, STATE_COLORS):
            ax.barh(secs.index, secs[state], left=left, color=color, label=state)
            left += secs[state].values
        ax.set_xlim(0, secs.sum(axis=1).max() * 1.4)   # free space on the right for the legend
        ax.set_xlabel("Seconds")
        ax.legend(fontsize=7, loc="center right")

    def chart_hours(ax):
        hours = class_secs.groupby("Student").sum() / 3600
        ax.bar(hours.index, hours.values, color="#10283F")
        ax.set_ylabel("Hours in class")
        ax.tick_params(axis="x", rotation=30)

    def chart_emotions(ax):
        counts = emo.value_counts()
        ax.bar(counts.index, counts.values, color="#6B9080")
        ax.set_ylabel("Seconds")
        ax.tick_params(axis="x", rotation=30)

    def chart_timeline(ax):
        slot = pd.to_datetime(seen["Time"], format="%H:%M:%S").dt.floor("5min").dt.strftime("%H:%M")
        line = (seen["Attention"] == "Attentive").groupby(slot).mean() * 100
        ax.plot(range(len(line)), line.values, color="#6B9080", marker="o")
        step = max(1, len(line) // 8)
        ax.set_xticks(range(0, len(line), step))
        ax.set_xticklabels(line.index[::step], rotation=45)
        ax.set_ylim(0, 100)
        ax.set_ylabel("% attentive (5-minute blocks)")

    def chart_present(ax):
        present = data.groupby("Date")["Student"].nunique()
        ax.bar(present.index, present.values, color="#10283F")
        ax.set_ylabel("Students")
        ax.tick_params(axis="x", rotation=30)

    def finish(ax, title):
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold", color="#10283F")
        ax.spines[["top", "right"]].set_visible(False)

    charts = [("Attention by student", chart_attention), ("Attention states (seconds)", chart_breakdown),
              ("Hours in class by student", chart_hours), ("Emotions (seconds on camera)", chart_emotions),
              ("Attention through the day", chart_timeline), ("Students present per date", chart_present)]

    # the dashboard on the page
    st.caption(f"{start} to {end}, {len(students)} student(s)")
    cols = st.columns(3)
    for k, (label, value) in enumerate(kpis.items()):
        cols[k % 3].metric(label, value)
    cols = st.columns(2)
    for k, (title, draw) in enumerate(charts):
        fig, ax = plt.subplots(figsize=(6, 3.4))
        draw(ax)
        finish(ax, title)
        fig.tight_layout()
        cols[k % 2].pyplot(fig)
        plt.close(fig)

    # the same dashboard as a PDF (A4 pages, two charts per page)
    pdf = io.BytesIO()
    with PdfPages(pdf) as doc:
        for k in range(0, len(charts), 2):
            fig, axes = plt.subplots(2, 1, figsize=(8.27, 11.69))
            for ax, (title, draw) in zip(axes, charts[k:k + 2]):
                draw(ax)
                finish(ax, title)
            fig.subplots_adjust(top=0.60 if k == 0 else 0.94, bottom=0.08, hspace=0.6, left=0.16, right=0.95)
            if k == 0:
                fig.text(0.08, 0.95, "Class Mind: Class Dashboard", fontsize=22, fontweight="bold", color="#10283F")
                fig.text(0.08, 0.925, f"{start} to {end}  |  {len(students)} student(s)  |  created {bahrain_time():%Y-%m-%d %H:%M} Bahrain time",
                         fontsize=9, color="#4A6656")
                for j, (label, value) in enumerate(kpis.items()):
                    fig.text(0.08 + 0.45 * (j % 2), 0.86 - (j // 2) * 0.075, str(value), fontsize=22, fontweight="bold", color="#6B9080")
                    fig.text(0.08 + 0.45 * (j % 2), 0.838 - (j // 2) * 0.075, label, fontsize=10, color="#10283F")
            doc.savefig(fig)
            plt.close(fig)
    st.download_button("Download dashboard (PDF)", pdf.getvalue(), f"class_dashboard_{start}_to_{end}.pdf", "application/pdf")
    
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
        day = st.date_input("Date", value=bahrain_time().date()).strftime("%Y-%m-%d")
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
                row.update({f"{k} (s)": int(counts.get(k, 0)) for k in ["Attentive", "Looking away", "Side-talking", "Head down", "Sleepy", "Not visible"]})
                rows.append(row)
            if not rows:
                st.info("No attention data recorded for this date.")
            else:
                st.subheader(f"Attention on {day}")
                st.dataframe(pd.DataFrame(rows), hide_index=True)

                if "Emotion" in day_log.columns:    # missing if the log file is from before emotions were added
                    emotions = day_log[day_log["Emotion"].notna() & (day_log["Emotion"] != "")]
                    if not emotions.empty:
                        st.subheader(f"Emotions on {day} (seconds)")
                        st.dataframe(emotions.groupby(["Student", "Emotion"]).size().unstack(fill_value=0).reset_index(), hide_index=True)
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
