import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage
import altair as alt
import cv2
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer
from face_helper_fun import ( S, ATTENDANCE_PATH, LOG_PATH, LOG_COLUMNS,PROCESS_SIZE,snapshot,save_pickle,save_students,shrink,detect_faces,get_embedding,check_left,attendance_table,load_log,video_callback,bahrain_time,)

st.set_page_config(page_title="Class Mind", layout="wide")

EMAIL_EVENTS = ["Arrived", "Left class"]
EMAILS_PER_REFRESH = 3

SERVERS = {"gmail.com": ("smtp.gmail.com", 465), "outlook.com": ("smtp-mail.outlook.com", 587), "hotmail.com": ("smtp-mail.outlook.com", 587),}

EMB_COLS = [f"e{i}" for i in range(128)]
BACKUP_COLS = ["Student", "Parent_email"] + EMB_COLS
CHART_COLORS = [ "#6B9080", "#8FB5A0", "#A8C9AD", "#C3DCC4", "#D9E9D9", "#E8F0E9",]
CHART_TEXT = "#10283F"
CHART_GRID = "#E1E8E3"

def style_chart(chart):
    """Apply the shared Class Mind theme to an Altair chart."""
    return chart.configure( background="#FFFFFF", view=alt.ViewConfig(stroke=None),
        axis=alt.AxisConfig( labelColor=CHART_TEXT, titleColor=CHART_TEXT, gridColor=CHART_GRID, domainColor=CHART_GRID, tickColor=CHART_GRID, labelFont="Source Sans 3", titleFont="Source Sans 3", labelFontSize=11, titleFontSize=12,),
        legend=alt.LegendConfig(labelColor=CHART_TEXT, titleColor=CHART_TEXT, labelFont="Source Sans 3", titleFont="Source Sans 3", ),
        title=alt.TitleConfig( color=CHART_TEXT, font="Plus Jakarta Sans", fontSize=15, fontWeight="bold", anchor="start", ), )

# LIVE MONITORING / EMAIL NOTIFICATIONS
@st.fragment(run_every=2)
def live_view():
    today = bahrain_time().strftime("%Y-%m-%d")
    mail = S["settings"]["mail"]
    sent = 0

    for name, student_data in list(S["att"].get(today, {}).items()):
        student_data.setdefault("emailed", len(student_data["events"]))

        while student_data["emailed"] < len(student_data["events"]):
            when, event = student_data["events"][student_data["emailed"]]
            emailable = event in EMAIL_EVENTS and mail["on"]

            if emailable and sent == EMAILS_PER_REFRESH:
                break

            student_data["emailed"] += 1

            if not emailable:
                continue

            sent += 1
            to_addr = S["parents"].get(name)
            domain = mail["sender"].split("@")[-1].lower()

            if not to_addr or domain not in SERVERS:
                S["email_log"].append(f"{bahrain_time():%H:%M:%S}  skipped {name}: "
                    "no parent email saved, or sender is not a Gmail / " "Outlook / Hotmail address" )
                continue

            subject = ( f"{name} arrived at class"
                if event == "Arrived"
                else f"{name} left class")

            message_text = ( f"{name} arrived in class on {when[:10]} at {when[11:]}."
                if event == "Arrived"
                else f"{name} left class on {when[:10]}. " f"{name} was last seen in class at {when[11:]}")

            host, port = SERVERS[domain]
            msg = EmailMessage()
            msg["From"] = mail["sender"]
            msg["To"] = to_addr
            msg["Subject"] = subject
            msg.set_content( f"Dear parent,\n\n{message_text}\n\n"
                "This is an automated message from Class Mind."  )

            with ( smtplib.SMTP_SSL(host, port, timeout=20)
                if port == 465
                else smtplib.SMTP(host, port, timeout=20) ) as server:
                if port != 465:
                    server.starttls()

                server.login(mail["sender"], mail["password"])
                server.send_message(msg)

            S["email_log"].append( f"{bahrain_time():%H:%M:%S}  sent to {to_addr}: {subject}" )

    age = time.time() - S["last_process"] if S["last_process"] else None

    if age is None:
        st.info("Waiting for the camera. Press START above.")
    elif age < 5:
        st.success("Camera is connected and students are being tracked.")
    else:
        st.info("No camera frames received in the last few seconds.")

    st.subheader("Today's attendance")
    st.dataframe( attendance_table(snapshot(S["att"]), today, list(S["db"])), hide_index=True, )

    if mail["on"]:
        st.text("\n".join(S["email_log"][-5:]) or "No emails sent yet.")

# SESSION STATE AND NAVIGATION
st.session_state.setdefault("gone_secs", 60)
st.session_state.setdefault("sender_email", "")
st.session_state.setdefault("sender_password", "")

page = st.radio( "Navigate", ["Class", "Enroll", "Dashboard"], format_func=lambda selected_page: { "Class": "🎓  Class", "Enroll": "👤  Enroll", "Dashboard": "📊  Dashboard",}[selected_page],
    horizontal=True,label_visibility="collapsed",)
sender = st.session_state.sender_email.strip()
password = st.session_state.sender_password
S["settings"] = { "gone_secs": int(st.session_state.gone_secs), "mail": { "on": bool(sender and password), "sender": sender, "password": password, },}

# ENROLL PAGE
if page == "Enroll":
    st.header("Enroll students")

    with st.expander("Parent email notifications", expanded=False):
        st.text_input( "Sender email", key="sender_email", placeholder="you@gmail.com", )
        st.text_input( "Sender password / app password", type="password", key="sender_password", )
        sender = st.session_state.sender_email.strip()
        password = st.session_state.sender_password
        S["settings"]["mail"] = { "on": bool(sender and password), "sender": sender, "password": password,}
    name = st.text_input("Student name").strip()
    email = st.text_input("Parent email").strip()
    valid_email = "@" in email and "." in email.split("@")[-1]

    if email and not valid_email:
        st.caption("Please enter a valid email address.")

    tab_camera, tab_upload = st.tabs(["Take photo", "Upload photos"])

    shot = tab_camera.camera_input("Clear, front-facing photo")
    files = tab_upload.file_uploader( "Upload photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True, )
    uploads = ([shot] if shot else []) + list(files or [])
    images = [
        shrink(img, 1280)
        for img in (cv2.imdecode(
                np.frombuffer(upload.getvalue(), np.uint8),
                cv2.IMREAD_COLOR,)
            for upload in uploads )
        if img is not None]

    if st.button( "Enroll", disabled=not (name and valid_email and images), ):
        added = 0

        for img in images:
            faces = detect_faces(img)

            if faces:
                largest_face = max( faces, key=lambda face: face[2] * face[3], )
                S["db"].setdefault(name, []).append( get_embedding(img, largest_face))
                added += 1

        if added < len(images):
            st.warning( f"No face found in {len(images) - added} photo(s), skipped.")

        if added:
            S["parents"][name] = email
            save_students()
            st.success(f"Saved {name} (parent: {email})")

    st.subheader("Enrolled students")

    for student, embeddings in list(S["db"].items()):
        col1, col2 = st.columns([4, 1])

        col1.write( f"{student} ({len(embeddings)} photos) - " f"{S['parents'].get(student, 'no parent email')}")

        if col2.button("Remove", key=f"remove_{student}"):
            S["db"].pop(student, None)
            S["parents"].pop(student, None)
            save_students()
            st.rerun()
# DASHBOARD PAGE
elif page == "Dashboard":
    st.header("Dashboard")
    log = load_log().reindex(columns=LOG_COLUMNS)

    if log.empty:
        st.info("No data yet. Run a monitoring session first.")
        st.stop()

    dates = sorted(log["Date"].dropna().astype(str).unique())
    all_students = sorted(log["Student"].dropna().unique())
    col_start, col_end = st.columns(2)
    start = col_start.selectbox("From", dates, index=0)
    end = col_end.selectbox("To", dates, index=len(dates) - 1)

    if start > end:
        st.warning("The start date must be before the end date.")
        st.stop()

    students = st.multiselect( "Students", all_students, default=all_students, )

    if not students:
        st.info("Select at least one student.")
        st.stop()

    data = log[ (log["Date"].astype(str) >= start) & (log["Date"].astype(str) <= end) & log["Student"].isin(students)].copy()

    if data.empty:
        st.warning("No data for this selection.")
        st.stop()

    data["Visible"] = pd.to_numeric( data["Visible"], errors="coerce").fillna(0)
    data["Time_in_class_secs"] = pd.to_numeric(data["Time_in_class_secs"], errors="coerce").fillna(0)
    data["Times_left"] = pd.to_numeric(data["Times_left"], errors="coerce").fillna(0)
    seen = data[data["Visible"] == 1].copy()
    seen["Emotion"] = seen["Emotion"].fillna("")
    seen["Attention"] = seen["Attention"].fillna("Unknown")
    class_secs = data.groupby(["Date", "Student"])["Time_in_class_secs"].max()
    emo = seen.loc[seen["Emotion"] != "", "Emotion"]
    attention = (round(100 * (seen["Attention"] == "Attentive").mean(), 1)
        if not seen.empty
        else 0)

    kpis = {"Students": data["Student"].nunique(),
        "Days": data["Date"].nunique(),
        "Hours in class": round(class_secs.sum() / 3600, 1),
        "Average attention": f"{attention}%",
        "Times left class": int(data.groupby(["Date", "Student"])["Times_left"].max().sum()),
        "Most common emotion": ( emo.mode().iloc[0] if not emo.empty else "-"),}

    STATES = [ "Attentive", "Looking away", "Side-talking", "Head down", "Sleepy", "Not visible",]
    st.caption( f"{start} to {end} · {len(students)} selected student(s)")
    metric_columns = st.columns(3)
    for index, (label, value) in enumerate(kpis.items()):
        metric_columns[index % 3].metric(label, value)

    st.subheader("Class insights")

    # 1. Attention distribution
    attention_df = ( seen["Attention"].value_counts().rename_axis("State").reset_index(name="Records"))

    attention_chart = (alt.Chart(attention_df).mark_arc(innerRadius=65).encode(theta=alt.Theta("Records:Q"),
            color=alt.Color("State:N", scale=alt.Scale( domain=STATES, range=CHART_COLORS,),),
            tooltip=["State:N", "Records:Q"], ).properties(title="Attention distribution", height=280,))

    # 2. Attention by student and state
    heat = (data.groupby(["Student", "Attention"]).size().reset_index(name="Records"))
    heat_chart = (alt.Chart(heat).mark_rect(cornerRadius=3).encode(x=alt.X("Attention:N",sort=STATES,title=None,axis=alt.Axis(labelAngle=-35),),
            y=alt.Y("Student:N",title=None,sort=all_students,),
            color=alt.Color("Records:Q",scale=alt.Scale(scheme="greens"),legend=alt.Legend(title="Records"),),
            tooltip=["Student:N","Attention:N","Records:Q",],).properties(title="Attention states by student",height=280,))

    # 3. Time in class
    hours_df = (class_secs.groupby("Student").sum().div(3600).rename("Hours").reset_index())
    hours_chart = alt.layer(alt.Chart(hours_df).mark_rule(color="#C3DCC4", strokeWidth=3).encode(
            y=alt.Y("Student:N", sort="-x", title=None),
            x=alt.X("Hours:Q", title="Hours in class"),),
        alt.Chart(hours_df).mark_circle(size=130, color="#6B9080").encode(
            y=alt.Y("Student:N", sort="-x", title=None),
            x="Hours:Q",
            tooltip=["Student:N",alt.Tooltip("Hours:Q", format=".2f"),],),).properties(title="Hours in class by student", height=280,)

    # 4. Emotion distribution
    emotion_df = (emo.value_counts().rename_axis("Emotion").reset_index(name="Records"))
    emotion_chart = (alt.Chart(emotion_df).mark_arc(innerRadius=65).encode(theta=alt.Theta("Records:Q"),
            color=alt.Color( "Emotion:N",scale=alt.Scale(scheme="greens"),legend=alt.Legend(title="Emotion"),),
            tooltip=["Emotion:N", "Records:Q"],).properties(title="Recorded emotion distribution", height=280,))

    # 5. Attention over time
    timeline = seen.copy()
    timeline["Time slot"] = (pd.to_datetime(timeline["Time"],format="%H:%M:%S", errors="coerce",).dt.floor("5min").dt.strftime("%H:%M"))
    timeline = timeline.dropna(subset=["Time slot"])
    timeline = (timeline.groupby("Time slot")["Attention"].apply(lambda values: 100 * (values == "Attentive").mean()).rename("Attentive %").reset_index())
    timeline_chart = (alt.Chart(timeline).mark_line(point=True,strokeWidth=3,color="#6B9080",).encode(x=alt.X("Time slot:N",sort=None, title="Time", ),
            y=alt.Y( "Attentive %:Q", scale=alt.Scale(domain=[0, 100]),title="Attentive (%)",),
            tooltip=["Time slot:N", alt.Tooltip("Attentive %:Q", format=".1f"),],).properties(title="Attention throughout the day",height=280,))

    # 6. Daily attendance
    daily = (data.groupby("Date")["Student"].nunique().rename("Students").reset_index().sort_values("Date"))
    daily_chart = ( alt.Chart(daily).mark_area(line={"color": "#6B9080"},color="#A8C9AD",opacity=0.4,)
        .encode(x=alt.X( "Date:N",sort=None,title="Date",axis=alt.Axis(labelAngle=-35),),
        y=alt.Y( "Students:Q", title="Students recorded",scale=alt.Scale(zero=True),),
        tooltip=["Date:N", "Students:Q"],).properties(title="Daily attendance trend",height=280,))

    # Three charts in each row
    charts = [ attention_chart, heat_chart, hours_chart, emotion_chart, timeline_chart, daily_chart,]
    for index in range(0, len(charts), 3):
        chart_columns = st.columns(3, gap="medium")
        for column, chart in zip(chart_columns,charts[index:index + 3] ):
            with column:
                st.altair_chart(style_chart(chart),use_container_width=True)
    # PDF EXPORT
    def finish(ax, title):
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold", color="#10283F")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.2, color="#E1E8E3")

    def draw_attention(ax):
        counts = seen["Attention"].value_counts()
        if counts.empty:
            ax.text(0.5, 0.5, "No attention data", ha="center", va="center" )
        else:
            ax.pie( counts, labels=counts.index, autopct="%1.0f%%", startangle=90, colors=CHART_COLORS[:len(counts)],
                wedgeprops={ "width": 0.42, "edgecolor": "white" }, )
            ax.set_aspect("equal")

    def draw_heat(ax):
        matrix = ( data.groupby(["Student", "Attention"]).size().unstack(fill_value=0).reindex(columns=STATES, fill_value=0))

        if matrix.empty:
            ax.text( 0.5, 0.5, "No attention data", ha="center", va="center")
        else:
            im = ax.imshow( matrix.values, aspect="auto", cmap="Greens")
            ax.set_yticks( range(len(matrix)), matrix.index)
            ax.set_xticks( range(len(STATES)), STATES, rotation=30, ha="right")
            ax.figure.colorbar( im, ax=ax, label="Records" )

    def draw_hours(ax):
        hours = hours_df.sort_values("Hours")
        ax.hlines( hours["Student"], 0, hours["Hours"], color="#C3DCC4", linewidth=3)
        ax.scatter( hours["Hours"], hours["Student"], color="#6B9080", s=55 )
        ax.set_xlabel("Hours in class")

    def draw_emotions(ax):
        if emotion_df.empty:
            ax.text( 0.5, 0.5, "No emotion data", ha="center", va="center" )
        else:
            ax.pie( emotion_df["Records"], labels=emotion_df["Emotion"], autopct="%1.0f%%", startangle=90,
                colors=CHART_COLORS[:len(emotion_df)], wedgeprops={ "width": 0.42, "edgecolor": "white", })
            ax.set_aspect("equal")

    def draw_timeline(ax):
        if timeline.empty:
            ax.text( 0.5, 0.5, "No camera-visible data", ha="center", va="center",)
        else:
            ax.plot( timeline["Time slot"], timeline["Attentive %"], marker="o", color="#6B9080" )
            ax.set_ylim(0, 100)
            ax.set_ylabel("Attentive (%)")
            ax.tick_params(axis="x", rotation=35)

    def draw_daily(ax):
        ax.fill_between(range(len(daily)),daily["Students"],alpha=0.25,color="#A8C9AD")
        ax.plot( range(len(daily)), daily["Students"], marker="o", color="#6B9080")
        ax.set_xticks(range(len(daily)),daily["Date"], rotation=35)
        ax.set_ylabel("Students recorded")

    pdf_charts = [ ("Attention distribution", draw_attention),
        ("Attention states by student", draw_heat),
        ("Hours in class by student", draw_hours),
        ("Recorded emotion distribution", draw_emotions),
        ("Attention throughout the day", draw_timeline),
        ("Daily attendance trend", draw_daily)]
    pdf = io.BytesIO()

    with PdfPages(pdf) as document:
        for index in range(0, len(pdf_charts), 2):
            fig, axes = plt.subplots( 2, 1, figsize=(8.27, 11.69))
            for ax, (chart_title, draw_function) in zip( axes, pdf_charts[index:index + 2]):
                draw_function(ax)
                finish(ax, chart_title)

            fig.subplots_adjust(top=0.60 if index == 0 else 0.94, bottom=0.08, hspace=0.65, left=0.16, right=0.95 )

            if index == 0:
                fig.text( 0.08, 0.95, "Class Mind: Class Dashboard", fontsize=22, fontweight="bold", color="#10283F")
                fig.text( 0.08, 0.925, f"{start} to {end} | {len(students)} student(s) | " f"{bahrain_time():%Y-%m-%d %H:%M} Bahrain time", fontsize=9, color="#4A6656" )

                for j, (label, value) in enumerate(kpis.items()):
                    fig.text( 0.08 + 0.45 * (j % 2), 0.86 - (j // 2) * 0.075, str(value), fontsize=22, fontweight="bold", color="#6B9080")
                    fig.text( 0.08 + 0.45 * (j % 2), 0.838 - (j // 2) * 0.075, label, fontsize=10, color="#10283F" )

            document.savefig(fig)
            plt.close(fig)

    st.download_button("Download dashboard (PDF)", pdf.getvalue(), f"class_dashboard_{start}_to_{end}.pdf", "application/pdf",)

# CLASS PAGE
else:
    st.header("Class")
    gone_secs = st.number_input( "Mark as 'left class' after (seconds not seen)", 10, 1800, key="gone_secs")
    S["settings"]["gone_secs"] = int(gone_secs)
    tab_live, tab_report = st.tabs( ["Live monitoring", "Report"])

    with tab_live:
        if not S["db"]:
            st.warning("Enroll at least one student first.")
        else:
            st.write( "Press START, allow camera access, and keep this page "
                "open while class is in session. Use one browser tab "
                "with one camera at a time." )

            webrtc_streamer( key="classroom", mode=WebRtcMode.SENDRECV, rtc_configuration={ "iceServers": [ {
            "urls": [ "stun:stun.l.google.com:19302" ]}]}, media_stream_constraints={"video": {"width": {"ideal": PROCESS_SIZE},
            "height": {"ideal": int(PROCESS_SIZE * 0.75)}, "frameRate": {"ideal": 15},}, "audio": False }, video_frame_callback=video_callback,
            async_processing=True)

            live_view()

    with tab_report:
        att = snapshot(S["att"])
        names = list(S["db"])
        log = load_log()
        check_left(att, time.time(), gone_secs)
        day = st.date_input( "Date", value=bahrain_time().date(),).strftime("%Y-%m-%d")
        day_log = log[log["Date"] == day]
        tab_attendance, tab_attention, tab_log = st.tabs( ["Attendance", "Attention", "Log file"])

        with tab_attendance:
            table = attendance_table(att, day, names)

            if table.empty:
                st.info( "No students enrolled and no attendance recorded "  "for this date." )
            else:
                st.subheader(f"Class attendance on {day}")
                st.dataframe(table, hide_index=True)

            event_rows = [ {"Student": student, "Time": event_time, "Event": event}
                for student, student_data in att.get(day, {}).items()
                for event_time, event in student_data["events"]]

            if event_rows:
                with st.expander("Arrivals, departures and returns"):
                    st.dataframe(pd.DataFrame(event_rows).sort_values("Time"),hide_index=True)

            totals = {}
            for students_by_day in att.values():
                for student, student_data in students_by_day.items():
                    days, seconds = totals.get(student, (0, 0))
                    totals[student] = ( days + 1, seconds + student_data["present_secs"])

            if totals:
                with st.expander("Total hours across all days"):
                    st.dataframe(pd.DataFrame([{ "Student": student, "Days attended": days, "Total hours": round(seconds / 3600, 2) }
                                for student, (days, seconds) in totals.items()]), hide_index=True)

        with tab_attention:
            rows = []
            for student, group in day_log.groupby("Student"):
                counts = group["Attention"].value_counts()
                visible = int((group["Visible"] == 1).sum())

                row = {"Student": student,"Attention %": ( round(100 * counts.get("Attentive", 0) / visible,1)
                        if visible
                        else 0.0 ) }

                row.update( {f"{state} (s)": int(counts.get(state, 0))
                        for state in ["Attentive", "Looking away", "Side-talking", "Head down", "Sleepy", "Not visible"]})
                rows.append(row)

            if not rows:
                st.info("No attention data recorded for this date.")
            else:
                st.subheader(f"Attention on {day}")
                st.dataframe( pd.DataFrame(rows), hide_index=True)
                if "Emotion" in day_log.columns:
                    emotions = day_log[ day_log["Emotion"].notna() & (day_log["Emotion"] != "")]

                    if not emotions.empty:
                        st.subheader(f"Emotions on {day} (seconds)")
                        st.dataframe( emotions.groupby( ["Student", "Emotion"]).size().unstack(fill_value=0).reset_index(), hide_index=True)

        with tab_log:
            if day_log.empty:
                st.info("No log rows for this date.")
            else:
                st.caption( f"{len(day_log)} rows on {day} (showing the last 500)")
                st.dataframe( day_log.tail(500), hide_index=True )

            pairs = [(date, student, student_data) for date, students_by_day in att.items() for student, student_data in students_by_day.items()]

            summary = pd.DataFrame([{ "Date": date, "Student": student, "First_seen": student_data["first_seen"], "Last_seen_of_day": student_data["last_seen"]}
                    for date, student, student_data in pairs ],
                columns=[ "Date", "Student", "First_seen", "Last_seen_of_day", ])

            event_log = pd.DataFrame(
                [ { "Date": date, "Time": event_time[11:], "Student": student, "Event": event, "Status": ( "Left class"
                            if event == "Left class"
                            else "In class"
                    )}
                    for date, student, student_data in pairs
                    for event_time, event in student_data["events"]
                ])

            absent = pd.DataFrame(
                [{ "Date": date, "Student": student, "Status": "Absent", "Visible": 0, "Attention": "Absent", "Time_in_class_secs": 0, "Time_away_secs": 0, "Times_left": 0,}
                    for date, students_by_day in att.items()
                    for student in names
                    if student not in students_by_day])

            columns = LOG_COLUMNS + [ "Event", "First_seen", "Last_seen_of_day"]
            parts = [ part for part in ( log.assign(Event=""), event_log, absent) if not part.empty]

            if parts:
                full = pd.concat( parts, ignore_index=True).merge( summary, on=["Date", "Student"], how="left" )

                for column in [ "Visible", "Time_in_class_secs", "Time_away_secs", "Times_left"]:
                    full[column] = pd.to_numeric( full[column], errors="coerce" ).astype("Int64")
                full = full.sort_values( ["Date", "Time", "Student"])[columns]
            else:
                full = pd.DataFrame(columns=columns)

            st.download_button("Download full log (CSV)", full.to_csv(index=False), "class_log_full.csv", disabled=full.empty)
            st.caption( "On a cloud server the log is temporary: " "download it at the end of each day.")
            if st.button("Clear all data for this date"):
                S["att"].pop(day, None)
                save_pickle(ATTENDANCE_PATH, S["att"])
                remaining = load_log()
                if not remaining.empty:
                    remaining[remaining["Date"] != day].to_csv( LOG_PATH, index=False, )

                st.rerun()
