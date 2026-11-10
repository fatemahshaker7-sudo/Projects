from pathlib import Path
import joblib, librosa, numpy as np, streamlit as st

model = joblib.load(Path(__file__).parent / "pump00_0dB_model.joblib")   # path relative to this file
SR = 16000    # the model was trained on 10-second clips at 16 kHz

def predict(y):
    m = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=20)
    return model.predict_proba([np.concatenate([m.mean(axis=1), m.std(axis=1)])])[0, 1]

def show(p, box):
    (box.error if p > 0.5 else box.success)(f"{'Abnormal' if p > 0.5 else 'Normal'} (abnormal probability {p:.0%})")

st.title("Pump Fault Detector 🕳")
mode = st.radio("Choose input", ["Record in browser", "Upload clip"], horizontal=True)

if mode == "Record in browser":
    st.caption("Record about 10 seconds of the pump, then stop. Your browser will ask for microphone permission.")
    file = st.audio_input("Record a clip")
else:
    file = st.file_uploader("Upload a .wav clip", type="wav")
    if file:
        st.audio(file)

if file:
    file.seek(0)
    y, _ = librosa.load(file, sr=SR, mono=False)
    show(predict(y[0] if y.ndim > 1 else y), st.empty())
