# %%
import os
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow.keras import layers, models
from sklearn.metrics import ConfusionMatrixDisplay
import pandas as pd

# %%
# 1. Load images (folder names become the labels)

train = tf.keras.utils.image_dataset_from_directory(
    "archive/train", image_size=(48, 48), color_mode="grayscale",
    label_mode="categorical", batch_size=64,
    validation_split=0.2, subset="training", seed=42)

val = tf.keras.utils.image_dataset_from_directory(
    "archive/train", image_size=(48, 48), color_mode="grayscale",
    label_mode="categorical", batch_size=64,
    validation_split=0.2, subset="validation", seed=42)

test = tf.keras.utils.image_dataset_from_directory(
    "archive/test", image_size=(48, 48), color_mode="grayscale",
    label_mode="categorical", batch_size=64, shuffle = False)


# %%
# 2. Balance the data (class weights)  <-- NEW
counts = np.array([len(os.listdir(f"archive/train/{n}")) for n in train.class_names])
print(dict(zip(train.class_names, counts)))   # see how unbalanced it is

class_weight = dict(enumerate(counts.sum() / (len(counts) * counts)))
print(class_weight)
#pd.Series(train).value_counts()
# %%
print(train.class_names)
# %% show some images

for images, labels in train.take(1):
    for i in range(25):
        plt.subplot(5, 5, i + 1)
        plt.imshow(images[i].numpy().squeeze(), cmap="gray")
        plt.title(train.class_names[labels[i].numpy().argmax()])
        plt.axis("off")
plt.show()

# %% the model 
model = models.Sequential([
    layers.Input(shape=(48, 48, 1)),
    layers.Rescaling(1./255),

    # data augmentation (flip , rotation, zoom) works only while training
    layers.RandomFlip("horizontal"),
    layers.RandomRotation(0.1),
    layers.RandomZoom(0.1),

    layers.Conv2D(64, 3, padding="same", activation="relu"),
    layers.BatchNormalization(),
    layers.MaxPooling2D(),

    layers.Conv2D(128, 3, padding="same", activation="relu"),
    layers.BatchNormalization(),
    layers.MaxPooling2D(),

    layers.GlobalAveragePooling2D(),
    layers.Dropout(0.4),
    layers.Dense(7, activation="softmax"),
])


# %% compiling the model
model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
# %% fitting
# 3. Train and test
early_stop = tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)

history = model.fit(train, validation_data=val, epochs=20, callbacks=[early_stop], class_weight=class_weight)

model.summary()
# %%
model.evaluate(test)

# %% check the confusion matrix with the test
y_test = np.concatenate([y.numpy().argmax(axis=1) for x, y in test])
y_pred = model.predict(test).argmax(axis=1)

ConfusionMatrixDisplay.from_predictions(y_test, y_pred, display_labels=test.class_names, xticks_rotation="vertical")
plt.show()
# %%
# 4. Save
model.save("emotion_model2.keras")

# %%
