import os
import numpy as np
import streamlit as st
import tensorflow as tf
from PIL import Image

st.set_page_config(page_title="Age & Gender Estimator")

st.title("Age & Gender Estimator")
st.caption("Take a photo or upload one with a clear, front-facing face.")

GENDER = ["Male", "Female"]
COLOR = ["blue", "violet"] 

@st.cache_resource
def load_model():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "age_gender_model.keras")
    return tf.keras.models.load_model(path)

model = load_model()

photo = st.camera_input("Take a photo") or st.file_uploader("...or upload one", type=["jpg", "jpeg", "png"])

if photo:
    img = Image.open(photo).convert("RGB")
    x = np.array(img.resize((64, 64)), dtype="float32").reshape(1, 64, 64, 3) / 255.0
    age, gender = model.predict(x, verbose=0)

    age = max(float(age[0, 0]), 0)
    p_female = float(gender[0, 0])
    g = round(p_female)
    confidence = max(p_female, 1 - p_female) * 100

    _, mid, _ = st.columns(3)
    mid.image(img)

    c1, c2 = st.columns(2)
    with c1.container(border=True):
        st.caption("ESTIMATED AGE")
        st.header(f":green[{age:.0f}]")
        st.caption("years (±9)")
    with c2.container(border=True):
        st.caption("GENDER")
        st.header(f":{COLOR[g]}[{GENDER[g]}]")
        st.caption(f"{confidence:.0f}% confident")