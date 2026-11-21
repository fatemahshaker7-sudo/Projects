# Class Mind 🧠 [![Streamlit App](https://img.shields.io/badge/Streamlit-Live%20Demo-FF4B4B?logo=streamlit&logoColor=white)](https://class-mind2.streamlit.app/)

Recognizing students and tracking their attention in class from a live camera, using pretrained face models.
Data Science Capstone | Prototype stage
 
## Problem Statement 🎯
 
Taking attendance by roll call uses up class time, and a teacher can't watch every student's attention at once. Drowsy or distracted students are usually noticed late, if at all, and there is no record of how attention changed during the lesson.
 
**Challenge:** can a model recognize enrolled students from a live camera, record when they arrive, and flag whether each one is attentive, looking away or has their eyes closed? This prototype tests that with one enrollment photo per student and a standard webcam.
 
## Impact 📈
 
* **Less class time lost:** attendance is recorded automatically as students appear on camera.
* **Attention insight for teachers:** a log shows when each student looked away or had their eyes closed, so lessons can be adjusted.
* **Low-cost setup:** one webcam and a laptop, no special sensors.
* **Privacy by design (partly):** uploaded photos are used once to compute face embeddings and are not saved. Only the embeddings (`embeddings.npz`) are kept.
**Early result (preliminary):**
 
Metrics reported by the `face_recognition` library for its pretrained model (not measured by this project):
 
| Metric | Value | Source |
|---|---|---|
| Accuracy on the Labeled Faces in the Wild (LFW) benchmark | 99.38% | `face_recognition` README |
| Face embedding size | 128 numbers per face | `face_recognition` API docs |
| Default match tolerance (Euclidean distance) | 0.6 (lower = stricter) | `face_recognition` API docs (`compare_faces`) |
 
Limitations stated by the library:
 
* The model is trained on adults and tends to mix up children at the default 0.6 threshold.
* Accuracy may vary between ethnic groups.
 
Results measured in this project (to be filled after testing with real students):
 
| Metric | Result |
|---|---|
| Students tested | _to be filled_ |
| Correct name when an enrolled student is on camera | _to be filled_ |
| Wrong name (matched to the wrong student) | _to be filled_ |
| Enrolled student not recognized | _to be filled_ |
| Attention states agreeing with a human observer | _to be filled_ |
 
This prototype shows feasibility, not final performance.
 
## Scope 🔍
 
* **Data:** no training dataset. One clear front-facing photo per student for enrollment (file name = student name), and a live webcam stream during class.
* **Approach:** pretrained dlib models through the `face_recognition` library: face detection, 68-point landmarks and 128-number face embeddings. A face is matched to the closest enrolled student by Euclidean distance (`face_distance`, cutoff 0.6). Attention is rule-based: eyes closed when the eye aspect ratio is below 0.20, and looking away when the nose tip is far from the center between the eyes. One record per student is saved about every 2 seconds.
* **Audience:** teachers, school administrators and capstone reviewers.
* **Deliverables:** Streamlit app (`stu_app.py`), helper module for deployment (`face_helper_fun.py`), attendance and attention log (CSV download), final presentation.
* **Next:** tune the thresholds on real classroom data, detect looking down (for example at a phone), use several photos per student, test recognition across different students (head coverings, glasses, lighting), add automatic report refresh, and deploy privately.
* **Responsible use:** use only with the knowledge and consent of students (or guardians) and according to the school's privacy policy. Attention states are rough indicators, not a measure of learning, and should not be the only basis for any decision about a student.

## Quick Start ⚡
 
```
pip install -r requirements.txt
streamlit run stu_app.py
```
 
1. **Enroll:** upload the student photos (file name = student name, for example `Ahmed_Ali.jpg`).
2. **Live class:** press START and allow camera access.
3. **Reports:** press Refresh to see attendance and state counts, and download the full log as a CSV file.
