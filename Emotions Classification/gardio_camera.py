import numpy as np
import gradio as gr
import tensorflow as tf
from PIL import Image

model = tf.keras.models.load_model("emotion_model2.keras")
LABELS = ["Angry", "Disgust", "Fear", "Happy", "Neutral", "Sad", "Surprise"]

def predict(img):
    img = Image.fromarray(img).convert("L").resize((48, 48))
    x = np.array(img, dtype="float32")          # no /255, the model does it
    probs = model.predict(x.reshape(1, 48, 48, 1), verbose=0)[0]
    return {l: float(p) for l, p in zip(LABELS, probs)}

gr.Interface(
    fn=predict,
    inputs=gr.Image(sources=["webcam", "upload"]),
    outputs=gr.Label(num_top_classes=3),
).launch()