import os
import numpy as np
import streamlit as st
import tensorflow as tf
from PIL import Image

LABELS = ["Angry", "Disgust", "Fear", "Happy", "Neutral", "Sad", "Surprise"]

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emotion_model2.keras")
model = tf.keras.models.load_model(path)

photo = st.camera_input("Take a photo") or st.file_uploader("...or upload one", type=["jpg", "jpeg", "png"])

if photo:
    img = Image.open(photo).convert("L").resize((48, 48))
    probs = model.predict(np.array(img, dtype="float32").reshape(1, 48, 48, 1), verbose=0)[0]
    st.write("Prediction:", LABELS[probs.argmax()])
    st.bar_chart(dict(zip(LABELS, probs.tolist())))