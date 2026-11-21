"""Helper functions and shared data for Class Mind."""
import os
import pickle
import tempfile
import time
from datetime import datetime, timedelta, timezoneimport av
import cv2
import mediapipe as mp
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = BASE if os.access(BASE, os.W_OK) else tempfile.gettempdir()
DETECTOR_PATH = os.path.join(BASE, "face_detection_yunet_2023mar.onnx")
RECOGNIZER_PATH = os.path.join(BASE, "face_recognition_sface_2021dec.onnx")
EMOTION_PATH = os.path.join(BASE, "emotion-ferplus-8.onnx")
EMOTIONS = ["Neutral", "Happy", "Surprised", "Sad", "Angry", "Disgusted", "Fearful", "Contempt"]
DB_PATH = os.path.join(DATA_DIR, "students.pkl")
PARENTS_PATH = os.path.join(DATA_DIR, "parents.pkl")
ATTENDANCE_PATH = os.path.join(DATA_DIR, "attendance.pkl")
LOG_PATH = os.path.join(DATA_DIR, "class_log.csv")

# Thresholds
MATCH_THRESHOLD = 0.363
EAR_CLOSED = 0.18        # eyes closed below this ratio
YAW_LOW, YAW_HIGH = 0.35, 0.65   # 0.5 = facing the camera
PITCH_DOWN = 0.70        # head tilted down above this
TALK_STD = 0.03          # mouth movement = talking
EYES_SECS, AWAY_SECS, DOWN_SECS = 2.0, 3.0, 3.0   # time for each condition

# Speed settings
PROCESS_EVERY = 0.4      # analyse the video about 2-3 times per second
PROCESS_SIZE = 640       # frames are shrunk to this width before analysis
VISIBLE_SECS = 2.0       # a student counts as "visible" if seen within this many seconds

COLORS = {"Attentive": (0, 200, 0), "Looking away": (0, 165, 255), "Side-talking": (0, 100, 255), "Head down": (255, 150, 0), "Sleepy": (0, 0, 255)}
LOG_COLUMNS = ["Date", "Time", "Student", "Status", "Visible", "Attention", "Emotion", "Time_in_class_secs", "Time_away_secs", "Times_left"]
BAHRAIN = timezone(timedelta(hours=3))   # Bahrain time (UTC+3, no daylight saving)

def bahrain_time(ts=None):
    """The current time (or the given timestamp) as Bahrain time."""
    return datetime.fromtimestamp(time.time() if ts is None else ts, BAHRAIN)
    
for path in (DETECTOR_PATH, RECOGNIZER_PATH, EMOTION_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing model file: {os.path.basename(path)}. Put it in the repository next to app.py.")

def load_pickle(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return {}

def save_pickle(path, data):
    """On a cloud server these files can disappear when the app restarts."""
    raw = pickle.dumps(data)
    with open(path, "wb") as f:
        f.write(raw)

def snapshot(data):
    """A copy of shared data (the video keeps updating the original)."""
    return pickle.loads(pickle.dumps(data))

# Everything the video and the pages share. A module is loaded only once, so this is created once.
S = {"detector": cv2.FaceDetectorYN.create(DETECTOR_PATH, "", (320, 320), score_threshold=0.8),
     "recognizer": cv2.FaceRecognizerSF.create(RECOGNIZER_PATH, ""),
     "emotion_net": cv2.dnn.readNetFromONNX(EMOTION_PATH),
     "face_mesh": mp.solutions.face_mesh.FaceMesh(max_num_faces=20, refine_landmarks=True),
     "db": load_pickle(DB_PATH),              # { "Sara": [embedding, ...] }
     "parents": load_pickle(PARENTS_PATH),    # { "Sara": "parent@example.com" }
     "att": load_pickle(ATTENDANCE_PATH),     # attendance memory, see video_callback
     "settings": {"gone_secs": 60, "debug": False, "mail": {"on": False, "sender": "", "password": ""}},
     "states": {}, "latest": {},              # attention timers / last label per student
     "email_log": [], "overlay": [],
     "last_process": 0.0, "last_log": 0.0, "last_save": 0.0}

def shrink(img, max_side):
    scale = max_side / max(img.shape[:2])
    return cv2.resize(img, None, fx=scale, fy=scale) if scale < 1 else img

def detect_faces(img):
    S["detector"].setInputSize((img.shape[1], img.shape[0]))
    _, faces = S["detector"].detect(img)
    return faces if faces is not None else []

def get_embedding(img, face):
    return S["recognizer"].feature(S["recognizer"].alignCrop(img, face))

def seconds_true(state, key, condition, now):
    """How long (in seconds) a condition has been continuously true."""
    if not condition:
        state[key] = None
        return 0
    state[key] = state[key] or now
    return now - state[key]

def save_students():
    save_pickle(DB_PATH, S["db"])
    save_pickle(PARENTS_PATH, S["parents"])

def fmt_dt(ts):
    return bahrain_time(ts).strftime("%Y-%m-%d %H:%M:%S")

def fmt_duration(secs):
    secs = int(secs)
    return f"{secs // 3600}h {(secs % 3600) // 60:02d}m {secs % 60:02d}s"

def check_left(att, now, gone_secs):
    """Mark students who have not been seen for a while as 'Left class'."""
    for day in list(att.values()):
        for s in list(day.values()):
            if s["status"] == "In class" and now - s["last_ts"] > gone_secs:
                s["status"] = "Left class"
                s["left_count"] += 1
                s["events"].append([s["last_seen"], "Left class"])

def attendance_table(att, day, names):
    absent = {"status": "Absent", "first_seen": "-", "last_seen": "-", "present_secs": 0, "away_secs": 0, "left_count": 0}
    rows = []
    for name in sorted(set(names) | set(att.get(day, {}))):
        s = att.get(day, {}).get(name, absent)
        rows.append({"Student": name, "Status": s["status"], "First seen": s["first_seen"], "Last seen": s["last_seen"],
                     "Time in class": fmt_duration(s["present_secs"]), "Time away": fmt_duration(s["away_secs"]),
                     "Times left": s["left_count"], "Hours in class": round(s["present_secs"] / 3600, 2)})
    return pd.DataFrame(rows)

def load_log():
    if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 0:
        return pd.read_csv(LOG_PATH, on_bad_lines="skip")
    return pd.DataFrame(columns=LOG_COLUMNS)

# S["att"] layout:{ "2026-11-20": { "Sara": {first_seen, last_seen, last_ts, present_secs,away_secs, left_count, status, events, emailed} } }
def video_callback(frame):
    """Called by streamlit-webrtc for every camera frame."""
    img, now = frame.to_ndarray(format="bgr24"), time.time()
    gone_secs = S["settings"]["gone_secs"]

    # analyse the video a few times per second
    if now - S["last_process"] >= PROCESS_EVERY:
        S["last_process"] = now
        small = shrink(img, PROCESS_SIZE)
        h, w = small.shape[:2]
        mesh = S["face_mesh"].process(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
        faces = detect_faces(small)
        overlay = []

        for landmarks in mesh.multi_face_landmarks or []:
            pts = np.array([(p.x * w, p.y * h) for p in landmarks.landmark])
            cx, cy = pts.mean(axis=0)
            (x1, y1), (x2, y2) = pts.min(axis=0), pts.max(axis=0)
            box = (x1 / w, y1 / h, x2 / w, y2 / h)      # stored as fractions of the frame size

            # who is it? find the face box containing this mesh's center and compare with enrolled students
            name = "Unknown"
            for f in faces:
                if f[0] <= cx <= f[0] + f[2] and f[1] <= cy <= f[1] + f[3]:
                    face_box = f
                    emb = get_embedding(small, f)
                    scores = [(S["recognizer"].match(emb, e, cv2.FaceRecognizerSF_FR_COSINE), n)
                              for n, embs in list(S["db"].items()) for e in list(embs)]
                    score, best = max(scores, default=(-1, "Unknown"))
                    name = best if score >= MATCH_THRESHOLD else "Unknown"
                    break
            if name == "Unknown":
                overlay.append(box + ("Unknown", (150, 150, 150), ""))
                continue

            # attendance: first sighting of the day, last seen, time in class
            day = S["att"].setdefault(bahrain_time(now).strftime("%Y-%m-%d"), {})
            if name not in day:
                day[name] = {"first_seen": fmt_dt(now), "last_seen": fmt_dt(now), "last_ts": now,
                             "present_secs": 0, "away_secs": 0, "left_count": 0, "status": "In class",
                             "events": [[fmt_dt(now), "Arrived"]], "emailed": 0}
            else:
                s = day[name]
                gap = now - s["last_ts"]
                if gap <= gone_secs and s["status"] == "In class":
                    s["present_secs"] += gap          # short gaps still count as present
                else:
                    if s["status"] == "In class":     # left while nobody was checking
                        s["left_count"] += 1
                        s["events"].append([s["last_seen"], "Left class"])
                    s["away_secs"] += gap             # time spent out of class
                    s["status"] = "In class"
                    s["events"].append([fmt_dt(now), "Returned"])
                s["last_seen"], s["last_ts"] = fmt_dt(now), now

            # attention: eyes, head turn, head tilt and mouth movement from the face mesh
            dist = lambda a, b: np.linalg.norm(pts[a] - pts[b])
            ear = ((dist(385, 380) + dist(387, 373)) / (2 * dist(362, 263)) + (dist(160, 144) + dist(158, 153)) / (2 * dist(33, 133))) / 2
            yaw = (pts[1][0] - pts[234][0]) / (pts[454][0] - pts[234][0])
            pitch = (pts[1][1] - pts[10][1]) / (pts[152][1] - pts[10][1])
            state = S["states"].setdefault(name, {"closed": None, "away": None, "down": None, "mouth": []})
            state["mouth"] = (state["mouth"] + [dist(13, 14) / dist(78, 308)])[-30:]
            talking = len(state["mouth"]) > 15 and np.std(state["mouth"]) > TALK_STD
            closed = seconds_true(state, "closed", ear < EAR_CLOSED, now)
            away = seconds_true(state, "away", yaw < YAW_LOW or yaw > YAW_HIGH, now)
            down = seconds_true(state, "down", pitch > PITCH_DOWN, now)
            if down >= DOWN_SECS:
                label = "Head down"
            elif closed >= EYES_SECS:
                label = "Sleepy"
            elif away >= AWAY_SECS:
                label = "Side-talking" if talking else "Looking away"
            else:
                label = "Attentive"

            # emotion: crop the face from the video and let the pretrained model classify it
            fx, fy, fw, fh = [max(int(v), 0) for v in face_box[:4]]
            crop = cv2.cvtColor(small[fy:fy + fh, fx:fx + fw], cv2.COLOR_BGR2GRAY)
            votes = state.setdefault("emotions", [])
            if crop.size:
                S["emotion_net"].setInput(cv2.resize(crop, (64, 64)).reshape(1, 1, 64, 64).astype(np.float32))
                votes.append(EMOTIONS[int(np.argmax(S["emotion_net"].forward()))])
                del votes[:-10]                                  # keep the last 10 guesses
            emotion = max(set(votes), key=votes.count) if votes else "Neutral"   # most common = steadier result

            S["latest"][name] = {"ts": now, "label": label, "emotion": emotion}
            debug = f"ear {ear:.2f} yaw {yaw:.2f} pitch {pitch:.2f}" if S["settings"]["debug"] else ""
            overlay.append(box + (f"{name}: {label} ({emotion})", COLORS[label], debug))
        S["overlay"] = overlay

    # once per second: mark students who left, write log rows, save attendance
    if now - S["last_log"] >= 1:
        S["last_log"] = now
        today = bahrain_time(now).strftime("%Y-%m-%d")
        check_left(S["att"], now, gone_secs)

        rows = []
        for name, s in list(S["att"].get(today, {}).items()):    # one log row for every student who arrived today
            info = S["latest"].get(name)
            visible = info is not None and now - info["ts"] <= VISIBLE_SECS
            rows.append({"Date": today, "Time": bahrain_time(now).strftime("%H:%M:%S"),
                         "Student": name, "Status": s["status"], "Visible": int(visible),
                         "Attention": info["label"] if visible else "Not visible",
                         "Emotion": info["emotion"] if visible else "",
                         "Time_in_class_secs": round(s["present_secs"]),
                         "Time_away_secs": round(s["away_secs"]), "Times_left": s["left_count"]})
        if rows:
            pd.DataFrame(rows, columns=LOG_COLUMNS).to_csv(
                LOG_PATH, mode="a", header=not os.path.exists(LOG_PATH), index=False)
        if now - S["last_save"] > 5:
            save_pickle(ATTENDANCE_PATH, S["att"])
            S["last_save"] = now

    # draw the boxes and names on the video
    h, w = img.shape[:2]
    for x1, y1, x2, y2, text, color, debug in list(S["overlay"]):
        x1, y1, x2, y2 = int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, text, (x1, max(y1 - 8, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        if debug:
            cv2.putText(img, debug, (x1, y2 + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return av.VideoFrame.from_ndarray(img, format="bgr24")
