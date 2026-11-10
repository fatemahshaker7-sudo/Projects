import io
from pathlib import Path
import joblib, librosa, numpy as np, soundfile as sf, streamlit as st

try:                                   # CHANGE 1: sounddevice needs PortAudio + a local mic,
    import sounddevice as sd           # which hosted servers (Streamlit Cloud) don't have
except (OSError, ImportError):
    sd = None

model = joblib.load(Path(__file__).parent / "pump00_0dB_model.joblib")   # CHANGE 2: path relative to this file
SR, SEC = 16000, 10    # the model was trained on 10-second clips at 16 kHz

def predict(y):
    m = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=20)
    return model.predict_proba([np.concatenate([m.mean(axis=1), m.std(axis=1)])])[0, 1]

def show(p, box):
    (box.error if p > 0.5 else box.success)(f"{'Abnormal' if p > 0.5 else 'Normal'} (abnormal probability {p:.0%})")

def to_wav(y):
    buf = io.BytesIO()
    sf.write(buf, y, SR, format="WAV")
    return buf.getvalue()

st.title("Pump Fault Detector 🕳")
modes = (["Live microphone"] if sd else []) + ["Record in browser", "Upload clip"]   # CHANGE 3: browser mic for hosted use
mode = st.radio("Choose input", modes, horizontal=True)

if mode == "Live microphone":
    live = st.toggle("Start live monitoring")
    status, box, player = st.empty(), st.empty(), st.empty()

    # show the last recording and result again after the app reruns
    if "wav" in st.session_state:
        player.audio(st.session_state.wav, format="audio/wav")
        show(st.session_state.prob, box)

    while live:
        status.markdown("🔴 **Recording...**")
        y = sd.rec(SEC * SR, samplerate=SR, channels=1, dtype="float32")
        sd.wait()

        status.markdown("⚙️ **Analyzing...**")
        prob = predict(y[:, 0])

        st.session_state.wav = to_wav(y[:, 0])      # save the recording for replay
        st.session_state.prob = prob
        player.audio(st.session_state.wav, format="audio/wav")
        show(prob, box)

    status.markdown("⚪ **Not recording**")

else:
    file = st.audio_input("Record a clip") if mode == "Record in browser" else st.file_uploader("Upload a .wav clip", type="wav")
    if file:
        if mode == "Upload clip":
            st.audio(file)
        file.seek(0)
        y, _ = librosa.load(file, sr=SR, mono=False)
        show(predict(y[0] if y.ndim > 1 else y), st.empty())
