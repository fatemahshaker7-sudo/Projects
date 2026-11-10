# Industrial Sound Anomaly Detection 🔊

Detecting industrial machine faults from sound using machine learning.
*Data Science Capstone | Prototype stage*

[![Streamlit App](https://img.shields.io/badge/Streamlit-Live%20Demo-FF4B4B?logo=streamlit&logoColor=white)](https://sound-anomaly-detection.streamlit.app/)
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fatemahshaker7-sudo/Projects/blob/main/industrial-sound-anomaly-detection/Prototype/notebooks/capstone_audio_check.ipynb)


## Problem Statement 🎯

Industrial machines like pumps often fail with little warning, and faults are usually caught by periodic inspections or a technician noticing an odd sound. Manual listening doesn't scale and misses problems between checks.

**Challenge:** can a model listen to a machine and classify it as **normal** or **abnormal**, even in a noisy factory? This prototype tests that on one pump (ID 00) at the medium noise leve (0 dB).

## Impact 📈

- **Less unplanned downtime:** faults caught early can be repaired on a schedule.
- **Lower maintenance cost:** continuous monitoring reduces manual inspection rounds.
- **Low-cost sensing:** a microphone is cheaper and easier to install than many specialized sensors.

**Early result (preliminary):** on 230 held-out clips, a Random Forest reached 98% accuracy, 100% precision and 83% recall on abnormal sounds, with no false alarms (5 of 29 faults missed). This is one pump, so it shows feasibility, not final performance.

## Scope 🔍

- **Data:** [MIMII Dataset](https://zenodo.org/records/3384388), pump ID 00, 0 dB noise (10 s clips, 16 kHz).
- **Approach:** MFCC features (mean and standard deviation, 40 per clip) with a class-balanced Random Forest for binary classification.
- **Audience:** maintenance and reliability engineers, plant operators, and capstone reviewers.
- **Deliverables:** analysis notebook (`capstone_audio_check.ipynb`), trained model, Streamlit demo app (`pump_st.py`), evaluation results, final presentation.
- **Next:** add all pumps, other machines (fan, valve, slider) and noise levels (-6, 6 dB); compare models; test on unseen pumps; deploy.
- **Out of scope:** identifying the fault type, predicting remaining life, factory-hardware deployment.

## Quick Start ⚡

```bash
pip install -r requirements.txt
streamlit run pump_st.py
```
