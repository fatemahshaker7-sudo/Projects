# 🧠 Class Mind: AI Classroom Monitoring  [![Streamlit App](https://img.shields.io/badge/Streamlit-Live%20Demo-FF4B4B?logo=streamlit&logoColor=white)](https://class-mind2.streamlit.app/)


A Streamlit app that recognizes students through a camera to take attendance automatically, estimates their attention and emotion, emails parents when a child arrives or leaves, and saves a log the teacher can analyze in Excel.

---

## Problem statement & motivation

Taking attendance by hand wastes class time, and a teacher cannot watch every student's attention at once. Parents also rarely know right away when their child arrives or leaves.

Class Mind tries to solve this with one camera and free, pretrained models:

- Record who is in class and for how long, with no roll call.
- Give the teacher a rough attention signal for each student.
- Email parents when their child arrives or leaves.
- Save timestamped data (one row per student per second) for Excel dashboards.

This is a capstone prototype. It is not meant for grading or discipline.

---

## Dataset description & sources

No dataset was collected, and no model was trained. The project uses pretrained models:

| Job | Model | Source |
|---|---|---|
| Find faces | YuNet | OpenCV Zoo |
| Recognize students | SFace | OpenCV Zoo |
| Face landmarks (eyes, head, mouth) | MediaPipe Face Mesh | Google MediaPipe |
| Emotion | FER+ | ONNX Model Zoo, trained on the FER2013 dataset with FER+ labels |

The app creates these files while running (they stay out of Git because they contain personal data):

- `students.pkl`: face embeddings (numbers, not photos)
- `parents.pkl`: parent emails
- `attendance.pkl`: attendance records
- `class_log.csv`: one row per student per second, with date, time, student, status, visible, attention, emotion, and time in class or away

---

## Model architecture & training pipeline

There is no training. The app works as a pipeline of pretrained models plus simple rules:

```
Browser camera -> find face (YuNet) -> recognize student (SFace)
                                    -> attention rules (MediaPipe landmarks)
                                    -> emotion (FER+)
                                    -> attendance + log + parent emails
```

**Attention rules:**

| State | Rule |
|---|---|
| Looking away | Head turned sideways for 3 seconds or more |
| Side-talking | Looking away while the mouth is moving |
| Head down | Head tilted down for 3 seconds or more |
| Sleepy | Eyes closed for 2 seconds or more |
| Attentive | None of the above |

**Attendance rules:** a student is marked *Arrived* the first time they are seen each day, *Left class* if not seen for 60 seconds (adjustable), and *Returned* when seen again. Time in class and time away are counted. All times use Bahrain time (UTC+3).

---

## Evaluation results & baseline comparison

Not evaluated yet. The pretrained models are used as they are, and the attention rules use hand-picked thresholds.

---

## How to run the project

You need **Python 3.12**, a webcam and a browser.

**1. Create an environment**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**2. Install the packages.** Put this in `requirements.txt`:

```
streamlit>=1.37
streamlit-webrtc
mediapipe==0.10.14
opencv-contrib-python==4.10.0.84
numpy<2
pandas
protobuf>=4.25.3,<5
```

Then run:

```powershell
pip install -r requirements.txt
```

**3. Download the three models** into the project folder:

```powershell
curl.exe -L -o face_detection_yunet_2023mar.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
curl.exe -L -o face_recognition_sface_2021dec.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx
curl.exe -L -o emotion-ferplus-8.onnx https://github.com/spmallick/learnopencv/raw/master/Facial-Emotion-Recognition/emotion-ferplus-8.onnx
```

Each file should be several MB or more. A tiny file means the download failed.

**4. Start the app**

```powershell
python -m streamlit run stu_app.py
```

**5. Use it**

1. **Enroll:** enter the student's name and the parent's email, add a photo, and press Enroll.
2. **Class:** press START on the video and allow the camera.
3. **Sidebar:** enter the sender email and password to send parent emails (Gmail needs an App Password).
4. **Report:** choose a date to see attendance, attention and emotion, and download the full log (CSV).

**Deploying on Streamlit Community Cloud:** push the code, the three models, `requirements.txt` and a `packages.txt` (with the lines `libgl1`, `libglib2.0-0`, `libportaudio2`) to GitHub. Choose **Python 3.12** in the advanced settings, and reboot the app after each update. Saved files can disappear on the cloud, so download the students backup and the log regularly.

**If something fails:**
- `no attribute 'solutions'`: you are not on Python 3.12.
- `Failed to parse ONNX model`: a model file is missing or damaged, so download it again.

---

## Repo structure

```
AI-Classroom-Monitoring/
├── stu_app.py                           # the web app pages
├── face_helper_fun.py                   # models, video processing, attendance logic
├── face_detection_yunet_2023mar.onnx    # YuNet
├── face_recognition_sface_2021dec.onnx  # SFace
├── emotion-ferplus-8.onnx               # FER+
├── requirements.txt
├── packages.txt
├── .gitignore
└── README.md
```

---

## Limitations & future work

**Limitations**

- Not tested on real data yet, so treat the results as rough signals.
- "Head down" also happens when a student is writing.
- Emotion detection is weak, and most faces come out as neutral.
- Faces must be fairly large in the frame, so one webcam cannot cover a full classroom.
- On the cloud, data is temporary, there is no login, and everyone sees the same data.
- The Class page must stay open for tracking and emails to work.
- This processes student face data. Get consent from students and parents, follow local data-protection rules, and do not use it for grading or discipline.

**Future work**

- Test it on real classroom data and fill in the results table.
- Add a database and a login.

---

## Screenshots / demo

https://github.com/user-attachments/assets/639cbdcf-92f6-40b7-bf34-2f27d73132d4

**Live demo:** `(https://class-mind2.streamlit.app/)`

---

## License & acknowledgments

MIT License. Each pretrained model keeps its own license.

Thanks to MediaPipe, OpenCV and the OpenCV Zoo (YuNet, SFace), the ONNX Model Zoo (FER+), Streamlit and streamlit-webrtc. 

