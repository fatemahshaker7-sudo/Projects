import io
import smtplib
import time
from email.message import EmailMessage
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import altair as alt
import cv2
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer
from face_helper_fun import (S, ATTENDANCE_PATH, LOG_PATH, LOG_COLUMNS, PROCESS_SIZE, snapshot, save_pickle, save_students, shrink, detect_faces, get_embedding, check_left, attendance_table, load_log, video_callback, bahrain_time)

st.set_page_config(page_title="Class Mind", layout="wide")

def app_header():
    col1, col2 = st.columns([1, 5], vertical_alignment="center")

    with col1:
        st.image("assets/class_mind_logo.png", width=95)

    with col2:
        st.markdown("""
            <div style="padding-top: 5px;">
                <h1 style="
                    color: #10283F;
                    font-size: 34px;
                    margin-bottom: 0;
                    font-weight: 800;">
                    Class <span style="color: #159B70;">Mind</span>
                </h1>
                <p style="
                    color: #6B9080;
                    font-size: 13px;
                    letter-spacing: 2px;
                    margin-top: 0;">
                    MONITOR • ANALYZE • SUPPORT
                </p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <hr style="
            border: none;
            height: 2px;
            background: linear-gradient(
                to right, #159B70, #D9E9D9, transparent
            );
            margin-top: 5px;
            margin-bottom: 25px;">
    """, unsafe_allow_html=True)

EMAIL_EVENTS = ["Arrived", "Left class"]
EMAILS_PER_REFRESH = 3
SERVERS = {"gmail.com": ("smtp.gmail.com", 465),"outlook.com": ("smtp-mail.outlook.com", 587),"hotmail.com": ("smtp-mail.outlook.com", 587),}
CHART_COLORS = ["#6B9080", "#8FB5A0", "#A8C9AD", "#C3DCC4", "#D9E9D9", "#E8F0E9"]
CHART_TEXT = "#10283F"
CHART_GRID = "#E1E8E3"
STATES = ["Attentive", "Looking away", "Side-talking", "Head down", "Sleepy", "Not visible"]

# Settings live in one plain dict inside session_state. Widgets only *edit* it
# (through on_change callbacks), so the values survive page changes. Widget
# keys themselves are deleted by Streamlit when the widget is not on screen.
if "cfg" not in st.session_state:
    st.session_state["cfg"] = {"sender": "", "password": "", "gone_secs": 60}
cfg = st.session_state["cfg"]

def update_cfg(cfg_key, widget_key, strip=False):
    value = st.session_state[widget_key]
    cfg[cfg_key] = value.strip() if strip else value

def sync_settings():
    """Copy the settings into the shared data used by the video thread."""
    sender, password = cfg["sender"].strip(), cfg["password"]
    S["settings"] = {"gone_secs": int(cfg["gone_secs"]), "mail": {"on": bool(sender and password), "sender": sender, "password": password},}

sync_settings()

#  email
def log_email(text):
    S["email_log"].append(f"{bahrain_time():%H:%M:%S}  {text}")

def send_email(mail, to_addr, subject, body):
    """Send one email. Raises an exception if anything goes wrong."""
    domain = mail["sender"].split("@")[-1].lower()
    host, port = SERVERS[domain]
    msg = EmailMessage()
    msg["From"] = mail["sender"]
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(f"Dear parent,\n\n{body}\n\nThis is an automated message from Class Mind.")

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=20) as server:
            server.login(mail["sender"], mail["password"])
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(mail["sender"], mail["password"])
            server.send_message(msg)

def build_message(name, event, when):
    if event == "Arrived":
        return (f"{name} arrived at class",
                f"{name} arrived in class on {when[:10]} at {when[11:]}.")
    return (f"{name} left class",f"{name} left class on {when[:10]}. {name} was last seen in class at {when[11:]}.")

def process_emails(today):
    """Send pending Arrived / Left class emails (at most EMAILS_PER_REFRESH per call)."""
    mail = S["settings"]["mail"]
    if not mail["on"]:
        return  # leave events untouched so they are sent once mail is switched on

    domain = mail["sender"].split("@")[-1].lower()
    sent = 0

    for name, data in list(S["att"].get(today, {}).items()):
        data.setdefault("emailed", 0)
        while data["emailed"] < len(data["events"]):
            when, event = data["events"][data["emailed"]]

            if event not in EMAIL_EVENTS:
                data["emailed"] += 1
                continue
            if sent >= EMAILS_PER_REFRESH:
                return

            data["emailed"] += 1
            to_addr = S["parents"].get(name)
            if not to_addr:
                log_email(f"skipped {name}: no parent email saved")
                continue
            if domain not in SERVERS:
                log_email(f"skipped {name}: sender must be a Gmail / Outlook / Hotmail address")
                continue

            subject, body = build_message(name, event, when)
            sent += 1
            try:
                send_email(mail, to_addr, subject, body)
                log_email(f"sent to {to_addr}: {subject}")
            except Exception as exc:
                log_email(f"FAILED {to_addr}: {exc}")


#  charts
def style_chart(chart):
    """Apply the shared Class Mind theme to an Altair chart."""
    return chart.configure(
        background="transparent",
        view=alt.ViewConfig(stroke=None),
        axis=alt.AxisConfig(labelColor=CHART_TEXT, titleColor=CHART_TEXT, gridColor=CHART_GRID,
            domainColor=CHART_GRID, tickColor=CHART_GRID,labelFont="Source Sans 3", titleFont="Source Sans 3",
            labelFontSize=11, titleFontSize=12,), legend=alt.LegendConfig( labelColor=CHART_TEXT, titleColor=CHART_TEXT,
            labelFont="Source Sans 3", titleFont="Source Sans 3" ),
        title=alt.TitleConfig( color=CHART_TEXT, font="Plus Jakarta Sans", fontSize=15, fontWeight="bold", anchor="start") )


#  live monitoring
@st.fragment(run_every=2)
def live_view():
    today = bahrain_time().strftime("%Y-%m-%d")
    mail = S["settings"]["mail"]

    process_emails(today)

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
    else:
        st.caption("Email notifications are off. Enter the sender email and password on the Enroll page.")

#  navigation
_, middle, _ = st.columns([1, 2, 1])
with middle:
    page = st.segmented_control( "Navigate", ["Enroll", "Class", "Dashboard"], format_func=lambda p: {"Class": "🎓 Class", "Enroll": "👤 Enroll", "Dashboard": "📊 Dashboard"}[p], default="Enroll", label_visibility="collapsed", width="stretch", key="page_nav",) or "Enroll"
    app_header()
    
#  ENROLL
if page == "Enroll":
    st.header("Enroll students")

    with st.expander("Parent email notifications", expanded=False):
        st.text_input( "Sender email", value=cfg["sender"], key="w_sender", placeholder="you@gmail.com", on_change=update_cfg, args=("sender", "w_sender", True))
        st.text_input( "Sender password / app password", value=cfg["password"], type="password", key="w_password", on_change=update_cfg, args=("password", "w_password"))
        st.caption("Gmail needs an App Password (2-Step Verification must be on).")
        sync_settings()
        if S["settings"]["mail"]["on"]:
            st.success("Email notifications are on.")
        else:
            st.info("Email notifications are off.")

    name = st.text_input("Student name").strip()
    email = st.text_input("Parent email").strip()
    valid_email = "@" in email and "." in email.split("@")[-1]
    if email and not valid_email:
        st.caption("Please enter a valid email address.")

    tab_camera, tab_upload = st.tabs(["Take photo", "Upload photos"])
    shot = tab_camera.camera_input("Clear, front-facing photo")
    files = tab_upload.file_uploader( "Upload photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    uploads = ([shot] if shot else []) + list(files or [])
    decoded = (cv2.imdecode(np.frombuffer(u.getvalue(), np.uint8), cv2.IMREAD_COLOR) for u in uploads)
    images = [shrink(img, 1280) for img in decoded if img is not None]

    if st.button("Enroll", disabled=not (name and valid_email and images)):
        added = 0
        for img in images:
            faces = detect_faces(img)
            if len(faces) > 0:
                largest = max(faces, key=lambda f: f[2] * f[3])
                S["db"].setdefault(name, []).append(get_embedding(img, largest))
                added += 1

        if added < len(images):
            st.warning(f"No face found in {len(images) - added} photo(s), skipped.")
        if added:
            S["parents"][name] = email
            save_students()
            st.success(f"Saved {name} (parent: {email})")

    st.subheader("Enrolled students")
    for student, embeddings in list(S["db"].items()):
        col1, col2 = st.columns([4, 1])
        col1.write(f"{student} ({len(embeddings)} photos) - {S['parents'].get(student, 'no parent email')}")
        if col2.button("Remove", key=f"remove_{student}"):
            S["db"].pop(student, None)
            S["parents"].pop(student, None)
            save_students()
            st.rerun()

#  DASHBOARD
elif page == "Dashboard":
    st.header("Dashboard")
    log = load_log().reindex(columns=LOG_COLUMNS)

    if log.empty:
        st.info("No data yet. Run a monitoring session first.")
        st.stop()

    dates = sorted(log["Date"].dropna().astype(str).unique())
    all_students = sorted(log["Student"].dropna().unique())

    with st.container(border=True):
        f1, f2, f3 = st.columns([1, 1, 3])
        start = f1.selectbox("From", dates, index=0)
        end = f2.selectbox("To", dates, index=len(dates) - 1)
        students = f3.multiselect("Students", all_students, default=all_students)

    if start > end:
        st.warning("The start date must be before the end date.")
        st.stop()
    if not students:
        st.info("Select at least one student.")
        st.stop()

    date_str = log["Date"].astype(str)
    data = log[(date_str >= start) & (date_str <= end) & log["Student"].isin(students)].copy()
    if data.empty:
        st.warning("No data for this selection.")
        st.stop()

    #  data prep
    for col in ["Visible", "Time_in_class_secs", "Times_left"]:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

    seen = data[data["Visible"] == 1].copy()
    seen["Emotion"] = seen["Emotion"].fillna("")
    seen["Attention"] = seen["Attention"].fillna("Unknown")

    class_secs = data.groupby(["Date", "Student"])["Time_in_class_secs"].max()
    emo = seen.loc[seen["Emotion"] != "", "Emotion"]
    attention = round(100 * (seen["Attention"] == "Attentive").mean(), 1) if not seen.empty else 0

    kpis = { "Students": data["Student"].nunique(),
        "Days": data["Date"].nunique(),"Hours in class": round(class_secs.sum() / 3600, 1),
        "Average attention": f"{attention}%","Times left class": int(data.groupby(["Date", "Student"])["Times_left"].max().sum()),
        "Most common emotion": emo.mode().iloc[0] if not emo.empty else "-"}

    st.caption(f"{start} to {end} · {len(students)} selected student(s)")
    for col, (label, value) in zip(st.columns(len(kpis)), kpis.items()):
        with col.container(border=True):
            st.metric(label, value)

    #  chart data
    attention_df = seen["Attention"].value_counts().rename_axis("State").reset_index(name="Records")
    heat = data.groupby(["Student", "Attention"]).size().reset_index(name="Records")
    hours_df = class_secs.groupby("Student").sum().div(3600).rename("Hours").reset_index()
    emotion_df = emo.value_counts().rename_axis("Emotion").reset_index(name="Records")

    timeline = seen.copy()
    timeline["Time slot"] = ( pd.to_datetime(timeline["Time"], format="%H:%M:%S", errors="coerce").dt.floor("5min").dt.strftime("%H:%M"))
    timeline = timeline.dropna(subset=["Time slot"])
    timeline = (timeline.groupby("Time slot")["Attention"].apply(lambda v: 100 * (v == "Attentive").mean()).rename("Attentive %").reset_index())
    daily = (data.groupby("Date")["Student"].nunique().rename("Students").reset_index().sort_values("Date"))

    #  altair charts
    H = 260
    attention_chart = (alt.Chart(attention_df).mark_arc(innerRadius=60).encode(theta=alt.Theta("Records:Q"), color=alt.Color("State:N", scale=alt.Scale(domain=STATES, range=CHART_COLORS)),
                tooltip=["State:N", "Records:Q"]).properties(height=H))

    heat_chart = (alt.Chart(heat).mark_rect(cornerRadius=3).encode(x=alt.X("Attention:N", sort=STATES, title=None, axis=alt.Axis(labelAngle=-30)),
                y=alt.Y("Student:N", title=None, sort=all_students),
                color=alt.Color("Records:Q", scale=alt.Scale(scheme="greens"),legend=alt.Legend(title="Records")),
                tooltip=["Student:N", "Attention:N", "Records:Q"]).properties(height=H))

    hours_chart = alt.layer(alt.Chart(hours_df).mark_rule(color="#C3DCC4", strokeWidth=3).encode(y=alt.Y("Student:N", sort="-x", title=None),
                x=alt.X("Hours:Q", title="Hours in class")), alt.Chart(hours_df).mark_circle(size=130, color="#6B9080").encode(y=alt.Y("Student:N", sort="-x", title=None), x="Hours:Q",
                tooltip=["Student:N", alt.Tooltip("Hours:Q", format=".2f")])).properties(height=H)

    emotion_chart = (alt.Chart(emotion_df).mark_arc(innerRadius=60).encode(theta=alt.Theta("Records:Q"),color=alt.Color("Emotion:N", scale=alt.Scale(scheme="greens"),
                    legend=alt.Legend(title="Emotion")),tooltip=["Emotion:N", "Records:Q"]).properties(height=H))

    timeline_chart = ( alt.Chart(timeline).mark_area(line={"color": "#6B9080", "strokeWidth": 3}, color="#A8C9AD", opacity=0.35, point=True).encode(x=alt.X("Time slot:N", sort=None, title="Time"),
                y=alt.Y("Attentive %:Q", scale=alt.Scale(domain=[0, 100]), title="Attentive (%)"),
                tooltip=["Time slot:N", alt.Tooltip("Attentive %:Q", format=".1f")]).properties(height=H))

    daily_chart = (alt.Chart(daily).mark_bar(color="#8FB5A0", cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(x=alt.X("Date:N", sort=None, title=None, axis=alt.Axis(labelAngle=-30)),
                y=alt.Y("Students:Q", title="Students recorded", scale=alt.Scale(zero=True)),
                tooltip=["Date:N", "Students:Q"]).properties(height=H))

    def card(column, title, chart, empty_text=None):
        """One bordered dashboard panel: title on top, chart (or empty note) below."""
        with column.container(border=True):
            st.markdown(f"**{title}**")
            if empty_text:
                st.caption(empty_text)
            else:
                st.altair_chart(style_chart(chart), width="stretch")

    st.subheader("Class insights")
    row1 = st.columns([2, 1], gap="medium")
    card(row1[0], "Attention throughout the day", timeline_chart, "No camera-visible data." if timeline.empty else None)
    card(row1[1], "Attention distribution", attention_chart, "No attention data." if attention_df.empty else None)

    row2 = st.columns([2, 1], gap="medium")
    card(row2[0], "Attention states by student", heat_chart)
    card(row2[1], "Recorded emotions", emotion_chart, "No emotion data." if emotion_df.empty else None)

    row3 = st.columns(2, gap="medium")
    card(row3[0], "Hours in class by student", hours_chart)
    card(row3[1], "Daily attendance", daily_chart)

    #  PDF export (built only when asked)
    def finish(ax, title):
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold", color=CHART_TEXT)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.2, color=CHART_GRID)

    def no_data(ax, text):
        ax.text(0.5, 0.5, text, ha="center", va="center")

    def donut(ax, values, labels):
        ax.pie(values, labels=labels, autopct="%1.0f%%", startangle=90,
               colors=CHART_COLORS[:len(values)], wedgeprops={"width": 0.42, "edgecolor": "white"})
        ax.set_aspect("equal")

    def draw_attention(ax):
        counts = seen["Attention"].value_counts()
        if counts.empty:
            no_data(ax, "No attention data")
        else:
            donut(ax, counts, counts.index)

    def draw_heat(ax):
        matrix = (data.groupby(["Student", "Attention"]).size().unstack(fill_value=0).reindex(columns=STATES, fill_value=0))
        if matrix.empty:
            no_data(ax, "No attention data")
        else:
            im = ax.imshow(matrix.values, aspect="auto", cmap="Greens")
            ax.set_yticks(range(len(matrix)), matrix.index)
            ax.set_xticks(range(len(STATES)), STATES, rotation=30, ha="right")
            ax.figure.colorbar(im, ax=ax, label="Records")

    def draw_hours(ax):
        hours = hours_df.sort_values("Hours")
        ax.hlines(hours["Student"], 0, hours["Hours"], color="#C3DCC4", linewidth=3)
        ax.scatter(hours["Hours"], hours["Student"], color="#6B9080", s=55)
        ax.set_xlabel("Hours in class")

    def draw_emotions(ax):
        if emotion_df.empty:
            no_data(ax, "No emotion data")
        else:
            donut(ax, emotion_df["Records"], emotion_df["Emotion"])

    def draw_timeline(ax):
        if timeline.empty:
            no_data(ax, "No camera-visible data")
        else:
            ax.plot(timeline["Time slot"], timeline["Attentive %"], marker="o", color="#6B9080")
            ax.set_ylim(0, 100)
            ax.set_ylabel("Attentive (%)")
            ax.tick_params(axis="x", rotation=35)

    def draw_daily(ax):
        ax.fill_between(range(len(daily)), daily["Students"], alpha=0.25, color="#A8C9AD")
        ax.plot(range(len(daily)), daily["Students"], marker="o", color="#6B9080")
        ax.set_xticks(range(len(daily)), daily["Date"], rotation=35)
        ax.set_ylabel("Students recorded")

    pdf_charts = [("Attention distribution", draw_attention),
        ("Attention states by student", draw_heat), ("Hours in class by student", draw_hours),
        ("Recorded emotion distribution", draw_emotions),("Attention throughout the day", draw_timeline),
        ("Daily attendance trend", draw_daily)]

    def build_pdf():
        buffer = io.BytesIO()
        with PdfPages(buffer) as document:
            for index in range(0, len(pdf_charts), 2):
                fig, axes = plt.subplots(2, 1, figsize=(8.27, 11.69))
                for ax, (chart_title, draw_function) in zip(axes, pdf_charts[index:index + 2]):
                    draw_function(ax)
                    finish(ax, chart_title)

                fig.subplots_adjust(top=0.60 if index == 0 else 0.94, bottom=0.08, hspace=0.65, left=0.16, right=0.95)

                if index == 0:
                    fig.text(0.08, 0.95, "Class Mind: Class Dashboard", fontsize=22, fontweight="bold", color=CHART_TEXT)
                    fig.text(0.08, 0.925, f"{start} to {end} | {len(students)} student(s) | " f"{bahrain_time():%Y-%m-%d %H:%M} Bahrain time", fontsize=9, color="#4A6656")
                    for j, (label, value) in enumerate(kpis.items()):
                        x = 0.08 + 0.45 * (j % 2)
                        y = 0.86 - (j // 2) * 0.075
                        fig.text(x, y, str(value), fontsize=22, fontweight="bold", color="#6B9080")
                        fig.text(x, y - 0.022, label, fontsize=10, color=CHART_TEXT)

                document.savefig(fig)
                plt.close(fig)
        return buffer.getvalue()

    with st.container(border=True):
        e1, e2 = st.columns([3, 1], vertical_alignment="center")
        e1.markdown("**Export**  \nDownload this view as a PDF report.")
        pdf_key = f"{start}|{end}|{','.join(students)}"
        if e2.button("Prepare PDF", width="stretch"):
            with st.spinner("Building PDF..."):
                st.session_state["pdf_bytes"] = build_pdf()
                st.session_state["pdf_key"] = pdf_key
        if st.session_state.get("pdf_key") == pdf_key:
            e2.download_button( "Download PDF", st.session_state["pdf_bytes"], f"class_dashboard_{start}_to_{end}.pdf", "application/pdf", width="stretch")


#  CLASS
else:
    st.header("Class")
    st.number_input( "Mark as 'left class' after (seconds not seen)", 10, 1800, value=int(cfg["gone_secs"]), key="w_gone_secs", on_change=update_cfg, args=("gone_secs", "w_gone_secs"))
    sync_settings()
    gone_secs = int(cfg["gone_secs"])

    tab_live, tab_report = st.tabs(["Live monitoring", "Report"])

    with tab_live:
        if not S["db"]:
            st.warning("Enroll at least one student first.")
        else:
            st.write("Press START, allow camera access, and keep this page open while " "class is in session. Use one browser tab with one camera at a time.")

            webrtc_streamer(
                key="classroom", mode=WebRtcMode.SENDRECV,
                rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
                media_stream_constraints={ "video": {"width": {"ideal": PROCESS_SIZE}, "height": {"ideal": int(PROCESS_SIZE * 0.75)}, "frameRate": {"ideal": 15}}, "audio": False},
                video_frame_callback=video_callback, async_processing=True)
            live_view()

    with tab_report:
        att = snapshot(S["att"])
        names = list(S["db"])
        log = load_log()
        check_left(att, time.time(), gone_secs)

        day = st.date_input("Date", value=bahrain_time().date()).strftime("%Y-%m-%d")
        day_log = log[log["Date"] == day]
        tab_attendance, tab_attention, tab_log = st.tabs(["Attendance", "Attention", "Log file"])

        # attendance
        with tab_attendance:
            table = attendance_table(att, day, names)
            if table.empty:
                st.info("No students enrolled and no attendance recorded for this date.")
            else:
                st.subheader(f"Class attendance on {day}")
                st.dataframe(table, hide_index=True)

            event_rows = [{"Student": student, "Time": event_time, "Event": event} for student, data in att.get(day, {}).items() for event_time, event in data["events"]]
            if event_rows:
                with st.expander("Arrivals, departures and returns"):
                    st.dataframe(pd.DataFrame(event_rows).sort_values("Time"), hide_index=True)

            totals = {}
            for by_day in att.values():
                for student, data in by_day.items():
                    days, seconds = totals.get(student, (0, 0))
                    totals[student] = (days + 1, seconds + data["present_secs"])
            if totals:
                with st.expander("Total hours across all days"):
                    st.dataframe(pd.DataFrame([{"Student": student, "Days attended": days, "Total hours": round(seconds / 3600, 2)} for student, (days, seconds) in totals.items()]), hide_index=True)

        #  attention
        with tab_attention:
            rows = []
            for student, group in day_log.groupby("Student"):
                counts = group["Attention"].value_counts()
                visible = int((group["Visible"] == 1).sum())
                row = { "Student": student, "Attention %": round(100 * counts.get("Attentive", 0) / visible, 1) if visible else 0.0}
                row.update({f"{state} (s)": int(counts.get(state, 0)) for state in STATES})
                rows.append(row)

            if not rows:
                st.info("No attention data recorded for this date.")
            else:
                st.subheader(f"Attention on {day}")
                st.dataframe(pd.DataFrame(rows), hide_index=True)

                if "Emotion" in day_log.columns:
                    emotions = day_log[day_log["Emotion"].notna() & (day_log["Emotion"] != "")]
                    if not emotions.empty:
                        st.subheader(f"Emotions on {day} (seconds)")
                        st.dataframe( emotions.groupby(["Student", "Emotion"]).size().unstack(fill_value=0).reset_index(),hide_index=True)

        #  log file
        with tab_log:
            if day_log.empty:
                st.info("No log rows for this date.")
            else:
                st.caption(f"{len(day_log)} rows on {day} (showing the last 500)")
                st.dataframe(day_log.tail(500), hide_index=True)

            pairs = [(date, student, data) for date, by_day in att.items() for student, data in by_day.items()]
            summary = pd.DataFrame([{"Date": d, "Student": s, "First_seen": x["first_seen"], "Last_seen_of_day": x["last_seen"]} for d, s, x in pairs], columns=["Date", "Student", "First_seen", "Last_seen_of_day"])
            event_log = pd.DataFrame([{"Date": d, "Time": t[11:], "Student": s, "Event": e, "Status": "Left class" if e == "Left class" else "In class"} for d, s, x in pairs for t, e in x["events"]])
            absent = pd.DataFrame([{"Date": d, "Student": s, "Status": "Absent", "Visible": 0, "Attention": "Absent", "Time_in_class_secs": 0, "Time_away_secs": 0, "Times_left": 0} for d, by_day in att.items() for s in names if s not in by_day])
            columns = LOG_COLUMNS + ["Event", "First_seen", "Last_seen_of_day"]
            parts = [p for p in (log.assign(Event=""), event_log, absent) if not p.empty]

            if parts:
                full = pd.concat(parts, ignore_index=True).merge(summary, on=["Date", "Student"], how="left")
                for column in ["Visible", "Time_in_class_secs", "Time_away_secs", "Times_left"]:
                    full[column] = pd.to_numeric(full[column], errors="coerce").astype("Int64")
                full = full.sort_values(["Date", "Time", "Student"])[columns]
            else:
                full = pd.DataFrame(columns=columns)

            st.download_button("Download full log (CSV)", full.to_csv(index=False), "class_log_full.csv", disabled=full.empty)
            st.caption("On a cloud server the log is temporary: download it at the end of each day.")

            if st.button("Clear all data for this date"):
                S["att"].pop(day, None)
                save_pickle(ATTENDANCE_PATH, S["att"])
                remaining = load_log()
                if not remaining.empty:
                    remaining[remaining["Date"] != day].to_csv(LOG_PATH, index=False)
                st.rerun()
