import os
import av
import streamlit as st
from streamlit_webrtc import webrtc_streamer
from ultralytics import YOLO
from PIL import Image

model = YOLO(os.path.join(os.path.dirname(__file__), "best.pt"))
st.title("Bahraini Currency Detector")
mode = st.radio("Choose input", ["Live camera", "Upload photo"], horizontal=True)

if mode == "Live camera":
    def detect(frame):
        img = frame.to_ndarray(format="bgr24")
        result = model(img, verbose=False)[0]
        return av.VideoFrame.from_ndarray(result.plot(), format="bgr24")
    webrtc_streamer(key="live",
        video_frame_callback=detect,
        media_stream_constraints={"video": True, "audio": False},
        desired_playing_state=True,)
else:
    photo = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"])
    if photo:
        result = model(Image.open(photo))[0]
        st.image(result.plot()[:, :, ::-1])
