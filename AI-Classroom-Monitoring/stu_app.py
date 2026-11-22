import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import smtplib, time
from datetime import datetime
from email.message import EmailMessage
import altair as alt
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

    dates, all_students = sorted(log["Date"].dropna().astype(str).unique()), sorted(log["Student"].dropna().unique())
    c1, c2 = st.columns(2)
    start = c1.selectbox("From", dates, index=0)
    end = c2.selectbox("To", dates, index=len(dates) - 1)
    if start > end:
        st.warning("The start date must be before the end date.")
        st.stop()
    students = st.multiselect("Students", all_students, default=all_students)
    if not students:
        st.info("Select at least one student.")
        st.stop()

    data = log[(log["Date"].astype(str) >= start) & (log["Date"].astype(str) <= end) & log["Student"].isin(students)].copy()
    if data.empty:
        st.warning("No data for this selection.")
        st.stop()

    data["Visible"] = pd.to_numeric(data["Visible"], errors="coerce").fillna(0)
    data["Time_in_class_secs"] = pd.to_numeric(data["Time_in_class_secs"], errors="coerce").fillna(0)
    data["Times_left"] = pd.to_numeric(data["Times_left"], errors="coerce").fillna(0)
    seen = data[data["Visible"] == 1].copy()
    seen["Emotion"] = seen["Emotion"].fillna("")
    seen["Attention"] = seen["Attention"].fillna("Unknown")
    class_secs = data.groupby(["Date", "Student"])["Time_in_class_secs"].max()
    emo = seen.loc[seen["Emotion"] != "", "Emotion"]
    attention = round(100 * (seen["Attention"] == "Attentive").mean(), 1) if not seen.empty else 0
    
    kpis = { "Students": data["Student"].nunique(),
        "Days": data["Date"].nunique(),
        "Hours in class": round(class_secs.sum() / 3600, 1),
        "Average attention": f"{attention}%",
        "Times left class": int(data.groupby(["Date", "Student"])["Times_left"].max().sum()),
        "Most common emotion": emo.mode().iloc[0] if not emo.empty else "-" }

    STATES = ["Attentive", "Looking away", "Side-talking", "Head down", "Sleepy", "Not visible"]
    COLORS = ["#6B9080", "#E9B44C", "#D1603D", "#4A6FA5", "#7D5BA6", "#B8C0BC"]
    st.caption(f"{start} to {end} · {len(students)} selected student(s)")
    cols = st.columns(3)
    for i, (label, value) in enumerate(kpis.items()):
        cols[i % 3].metric(label, value)

    st.subheader("Class insights")
    # 1. Attention distribution — donut chart
    attention_df = seen["Attention"].value_counts().rename_axis("State").reset_index(name="Records")
    attention_chart = alt.Chart(attention_df).mark_arc(innerRadius=65).encode(
        theta=alt.Theta("Records:Q"), color=alt.Color("State:N", scale=alt.Scale(domain=STATES, range=COLORS)),
        tooltip=["State:N", "Records:Q"]).properties(title="Attention distribution", height=300)

    # 2. Attention by student and state — heatmap
    heat = data.groupby(["Student", "Attention"]).size().reset_index(name="Records")
    heat_chart = alt.Chart(heat).mark_rect(cornerRadius=3).encode(
        x=alt.X("Attention:N", sort=STATES, title=None, axis=alt.Axis(labelAngle=-35)),
        y=alt.Y("Student:N", title=None, sort=all_students),
        color=alt.Color("Records:Q", scale=alt.Scale(scheme="tealblues")),
        tooltip=["Student:N", "Attention:N", "Records:Q"] ).properties(title="Attention states by student", height=300)

    # 3. Time in class — lollipop chart
    hours_df = class_secs.groupby("Student").sum().div(3600).rename("Hours").reset_index()
    hours_chart = alt.layer( alt.Chart(hours_df).mark_rule(color="#B8C0BC", strokeWidth=3).encode(
        y=alt.Y("Student:N", sort="-x", title=None), x=alt.X("Hours:Q", title="Hours in class") ),
        alt.Chart(hours_df).mark_circle(size=150, color="#6B9080").encode(
        y=alt.Y("Student:N", sort="-x", title=None), x="Hours:Q", tooltip=["Student:N", alt.Tooltip("Hours:Q", format=".2f")]) ).properties(title="Hours in class by student", height=300)

    # 4. Emotion distribution — donut chart
    emotion_df = emo.value_counts().rename_axis("Emotion").reset_index(name="Records")
    emotion_chart = alt.Chart(emotion_df).mark_arc(innerRadius=65).encode(
        theta=alt.Theta("Records:Q"), color=alt.Color("Emotion:N", legend=alt.Legend(title="Emotion")),
        tooltip=["Emotion:N", "Records:Q"] ).properties(title="Recorded emotion distribution", height=300)

    # 5. Attention over time — line chart in five-minute intervals
    timeline = seen.copy()
    timeline["Time slot"] = pd.to_datetime(timeline["Time"], format="%H:%M:%S", errors="coerce").dt.floor("5min").dt.strftime("%H:%M")
    timeline = timeline.dropna(subset=["Time slot"])
    timeline = timeline.groupby("Time slot")["Attention"].apply(lambda x: 100 * (x == "Attentive").mean()).rename("Attentive %").reset_index()
    timeline_chart = alt.Chart(timeline).mark_line(point=True, strokeWidth=3, color="#4A6FA5").encode(
        x=alt.X("Time slot:N", sort=None, title="Time"), y=alt.Y("Attentive %:Q", scale=alt.Scale(domain=[0, 100]), title="Attentive (%)"),
        tooltip=["Time slot:N", alt.Tooltip("Attentive %:Q", format=".1f")]).properties(title="Attention throughout the day", height=300)

    # 6. Daily attendance — area chart
    daily = data.groupby("Date")["Student"].nunique().rename("Students").reset_index().sort_values("Date")
    daily_chart = alt.Chart(daily).mark_area(line={"color": "#6B9080"}, color="#6B9080", opacity=.3).encode(
        x=alt.X("Date:N", sort=None, title="Date", axis=alt.Axis(labelAngle=-35)),
        y=alt.Y("Students:Q", title="Students recorded", scale=alt.Scale(zero=True)),
        tooltip=["Date:N", "Students:Q"] ).properties(title="Daily attendance trend", height=300)

    chart_pairs = [(attention_chart, "Attention distribution"), (heat_chart, "Attention states by student"),
        (hours_chart, "Hours in class by student"), (emotion_chart, "Recorded emotion distribution"),
        (timeline_chart, "Attention throughout the day"), (daily_chart, "Daily attendance trend") ]
    for i in range(0, len(chart_pairs), 2):
        c1, c2 = st.columns(2)
        for col, (chart, _) in zip((c1, c2), chart_pairs[i:i + 2]):
            col.altair_chart(chart, use_container_width=True)

    # PDF export uses Matplotlib; the on-page dashboard uses interactive Altair charts.
    def finish(ax, title):
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold", color="#10283F")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=.2)

    def draw_attention(ax):
        counts = seen["Attention"].value_counts()
        if counts.empty:
            ax.text(.5, .5, "No attention data", ha="center", va="center")
        else:
            ax.pie(counts, labels=counts.index, autopct="%1.0f%%", startangle=90, wedgeprops={"width": .42, "edgecolor": "white"})
            ax.set_aspect("equal")

    def draw_heat(ax):
        matrix = data.groupby(["Student", "Attention"]).size().unstack(fill_value=0).reindex(columns=STATES, fill_value=0)
        if matrix.empty:
            ax.text(.5, .5, "No attention data", ha="center", va="center")
        else:
            im = ax.imshow(matrix.values, aspect="auto", cmap="YlGnBu")
            ax.set_yticks(range(len(matrix)), matrix.index)
            ax.set_xticks(range(len(STATES)), STATES, rotation=30, ha="right")
            ax.figure.colorbar(im, ax=ax, label="Records")

    def draw_hours(ax):
        hours = hours_df.sort_values("Hours")
        ax.hlines(hours["Student"], 0, hours["Hours"], color="#B8C0BC", linewidth=3)
        ax.scatter(hours["Hours"], hours["Student"], color="#6B9080", s=55)
        ax.set_xlabel("Hours in class")

    def draw_emotions(ax):
        if emotion_df.empty:
            ax.text(.5, .5, "No emotion data", ha="center", va="center")
        else:
            ax.pie(emotion_df["Records"], labels=emotion_df["Emotion"], autopct="%1.0f%%", startangle=90, wedgeprops={"width": .42, "edgecolor": "white"})
            ax.set_aspect("equal")

    def draw_timeline(ax):
        if timeline.empty:
            ax.text(.5, .5, "No camera-visible data", ha="center", va="center")
        else:
            ax.plot(timeline["Time slot"], timeline["Attentive %"], marker="o", color="#4A6FA5")
            ax.set_ylim(0, 100)
            ax.set_ylabel("Attentive (%)")
            ax.tick_params(axis="x", rotation=35)

    def draw_daily(ax):
        ax.fill_between(range(len(daily)), daily["Students"], alpha=.2, color="#6B9080")
        ax.plot(range(len(daily)), daily["Students"], marker="o", color="#6B9080")
        ax.set_xticks(range(len(daily)), daily["Date"], rotation=35)
        ax.set_ylabel("Students recorded")

    pdf_charts = [ ("Attention distribution", draw_attention), ("Attention states by student", draw_heat),
        ("Hours in class by student", draw_hours), ("Recorded emotion distribution", draw_emotions),
        ("Attention throughout the day", draw_timeline), ("Daily attendance trend", draw_daily) ]
    
    pdf = io.BytesIO()
    with PdfPages(pdf) as doc:
        for k in range(0, len(pdf_charts), 2):
            fig, axes = plt.subplots(2, 1, figsize=(8.27, 11.69))
            for ax, (title, draw) in zip(axes, pdf_charts[k:k + 2]):
                draw(ax)
                finish(ax, title)
            fig.subplots_adjust(top=.60 if k == 0 else .94, bottom=.08, hspace=.65, left=.16, right=.95)
            if k == 0:
                fig.text(.08, .95, "Class Mind: Class Dashboard", fontsize=22, fontweight="bold", color="#10283F")
                fig.text(.08, .925, f"{start} to {end} | {len(students)} student(s) | {bahrain_time():%Y-%m-%d %H:%M} Bahrain time", fontsize=9, color="#4A6656")
                for j, (label, value) in enumerate(kpis.items()):
                    fig.text(.08 + .45 * (j % 2), .86 - (j // 2) * .075, str(value), fontsize=22, fontweight="bold", color="#6B9080")
                    fig.text(.08 + .45 * (j % 2), .838 - (j // 2) * .075, label, fontsize=10, color="#10283F")
            doc.savefig(fig)
            plt.close(fig)
    st.download_button("Download dashboard (PDF)", pdf.getvalue(), f"class_dashboard_{start}_to_{end}.pdf", "application/pdf")
else:
    tab_live, tab_report = st.tabs(["Live monitoring", "Report"])
    with tab_live:
        if not S["db"]:
            st.warning("Enroll at least one student first.")
        else:
            st.write("Press START, allow camera access, and keep this page open while class is in session. Use one browser tab with one camera at a time.")
            webrtc_streamer(key="classroom", mode=WebRtcMode.SENDRECV, rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}, media_stream_constraints={"video": {"width": {"ideal": PROCESS_SIZE}, "height": {"ideal": int(PROCESS_SIZE * 0.75)}, "frameRate": {"ideal": 15}}, "audio": False}, video_frame_callback=video_callback, async_processing=True)
            live_view()
    with tab_report:
        att, names, log = snapshot(S["att"]), list(S["db"]), load_log()
        check_left(att, time.time(), gone_secs)
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
                    st.dataframe(pd.DataFrame([{"Student": n, "Days attended": d, "Total hours": round(secs / 3600, 2)} for n, (d, secs) in totals.items()]), hide_index=True)
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
                if "Emotion" in day_log.columns:
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
            pairs = [(d, n, s) for d, students in att.items() for n, s in students.items()]
            summary = pd.DataFrame([{"Date": d, "Student": n, "First_seen": s["first_seen"], "Last_seen_of_day": s["last_seen"]} for d, n, s in pairs], columns=["Date", "Student", "First_seen", "Last_seen_of_day"])
            event_log = pd.DataFrame([{"Date": d, "Time": t[11:], "Student": n, "Event": e, "Status": "Left class" if e == "Left class" else "In class"} for d, n, s in pairs for t, e in s["events"]])
            absent = pd.DataFrame([{"Date": d, "Student": n, "Status": "Absent", "Visible": 0, "Attention": "Absent", "Time_in_class_secs": 0, "Time_away_secs": 0, "Times_left": 0} for d, students in att.items() for n in names if n not in students])
            cols = LOG_COLUMNS + ["Event", "First_seen", "Last_seen_of_day"]
            parts = [p for p in (log.assign(Event=""), event_log, absent) if not p.empty]
            if parts:
                full = pd.concat(parts, ignore_index=True).merge(summary, on=["Date", "Student"], how="left")
                for col in ["Visible", "Time_in_class_secs", "Time_away_secs", "Times_left"]:
                    full[col] = pd.to_numeric(full[col], errors="coerce").astype("Int64")
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
