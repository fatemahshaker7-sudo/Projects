import os
import numpy as np
import streamlit as st
import tensorflow as tf
from PIL import Image

st.set_page_config(page_title="Mood Mirror", page_icon="🪞", layout="centered")

LABELS = ["Angry", "Disgust", "Fear", "Happy", "Neutral", "Sad", "Surprise"]
STYLE = {
    "Angry":    ("😠", "#ff6b6b"),
    "Disgust":  ("🤢", "#8bc34a"),
    "Fear":     ("😨", "#9575cd"),
    "Happy":    ("😄", "#ffd54f"),
    "Neutral":  ("😐", "#90a4ae"),
    "Sad":      ("😢", "#64b5f6"),
    "Surprise": ("😲", "#ff9f43"),
}

@st.cache_resource
def load_model():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emotion_model2.keras")
    return tf.keras.models.load_model(path)

model = load_model()

st.markdown("<h1 style='text-align:center'>🪞 Mood Mirror</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:gray'>Show me your face, I'll read your mood.</p>",
            unsafe_allow_html=True)

tab_cam, tab_up = st.tabs(["📷 Camera", "📁 Upload"])
with tab_cam:
    cam = st.camera_input("Take a photo", label_visibility="collapsed")
with tab_up:
    up = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

photo = cam or up

if photo:
    img = Image.open(photo).convert("L").resize((48, 48))
    probs = model.predict(np.array(img, dtype="float32").reshape(1, 48, 48, 1), verbose=0)[0]
    label = LABELS[int(probs.argmax())]
    emoji, color = STYLE[label]

    st.markdown(
        f"""
        <div style="background:{color}22; border:2px solid {color}; border-radius:24px;
                    padding:30px; text-align:center; margin-top:20px;">
            <div style="font-size:90px; line-height:1">{emoji}</div>
            <div style="font-size:34px; font-weight:700; color:{color}; margin-top:10px">{label}</div>
            <div style="color:gray; margin-top:4px">{probs.max()*100:.0f}% sure</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
