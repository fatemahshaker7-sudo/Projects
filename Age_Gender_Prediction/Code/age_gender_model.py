# %%
# importing libraries
import os
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from tensorflow.keras import layers, models
import pandas as pd

# %% reading and preparing x,y 
DATA_DIR = "UTKFace"
IMG_SIZE = 64

files = os.listdir(DATA_DIR)

X = np.array([np.array(Image.open(f"{DATA_DIR}/{f}").convert("RGB").resize((IMG_SIZE, IMG_SIZE))) for f in files]).astype(np.float32) / 255.0
y_age, y_gender = np.array([f.split("_")[:2] for f in files], dtype=int).T
# %% Splitting the data and stratisfy for age group and gender
age_group = np.digitize(y_age, [20, 40, 60, 80])   # 5 age groups
strat = age_group * 2 + y_gender

X_train_val, X_test, age_train_val, age_test, gender_train_val, gender_test, strat_tv, _ = train_test_split(
    X, y_age, y_gender, strat, test_size=0.15, random_state=42, stratify=strat)

X_train, X_val, age_train, age_val, gender_train, gender_val = train_test_split(
    X_train_val, age_train_val, gender_train_val,
    test_size=0.15, random_state=42, stratify=strat_tv)
# %% checking shapes
print(X_train.shape, X_val.shape, X_test.shape)
# %% Visuilizing some images with there labels
# males are always 0
GENDER = ["Male", "Female"]

plt.figure(figsize=(10, 10))
for i in range(25):
    plt.subplot(5, 5, i + 1)
    plt.imshow(X_train[i])
    plt.title(f"{age_train[i]}, {GENDER[gender_train[i]]}", fontsize=9)
    plt.axis("off")
plt.show()
# %% the model to take the image and predict age and gender(functional)
inputs = layers.Input(shape=(64, 64, 3))
x = layers.Conv2D(32, 3, activation="relu")(inputs)
x = layers.MaxPooling2D()(x)
x = layers.Conv2D(64, 3, activation="relu")(x)
x = layers.MaxPooling2D()(x)
x = layers.Flatten()(x)
x = layers.Dense(64, activation="relu")(x)

age_out = layers.Dense(1, name="age")(x)
gender_out = layers.Dense(1, activation="sigmoid", name="gender")(x)
model = models.Model(inputs, [age_out, gender_out])

# %% setting the optimizer, loss functions and metrics
model.compile(optimizer="adam", loss={"age": "mae", "gender": "binary_crossentropy"},
              metrics={"gender": "accuracy"})

# %% fitting and saving to history for plotting later
history = model.fit(X_train, {"age": age_train, "gender": gender_train},
          validation_data=(X_val, {"age": age_val, "gender": gender_val}),
          epochs=20, batch_size=64)

# %% evaluating on test
model.evaluate(X_test, {"age": age_test, "gender": gender_test})
# %% plotting 
pd.DataFrame(history.history).plot(figsize=(10, 5))
plt.show()
# %% show random predictions with there labels
GENDER = ["Male", "Female"]

age_pred, gender_pred = model.predict(X_test)

plt.figure(figsize=(12, 12))
for i, j in enumerate(np.random.choice(len(X_test), 25, replace=False)):
    plt.subplot(5, 5, i + 1)
    plt.imshow(X_test[j])
    plt.title(f"True: {age_test[j]}, {GENDER[gender_test[j]]}\n" f"Pred: {age_pred[j, 0]:.0f}, {GENDER[round(gender_pred[j, 0])]}", fontsize=9)
    plt.axis("off")
plt.show()
# %% saving the model to use in the streamlit app
model.save("age_gender_model.keras")

# %%
