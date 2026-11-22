"""Calm Classroom style for Class Mind. Call apply_style() once, right after st.set_page_config()."""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@700&family=Source+Sans+3:wght@400;600;700&display=swap');

:root {
  --navy: #10283F;
  --sage: #6B9080;
  --bg: #F2F5F3;
  --card: #FFFFFF;
  --line: #E1E8E3;
  --muted: #4A6656;
  --sage-light: #EDF3EE;
  --sage-mid: #A8C9AD;
}

/* Page and fonts */
.stApp {
  background: var(--bg);
  color: var(--navy);
}

.stApp, .stApp p, .stApp label, .stApp li,
.stApp button, .stApp input, .stApp textarea {
  font-family: 'Source Sans 3', sans-serif;
}

h1, h2, h3, h4 {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  color: var(--navy);
  font-weight: 700;
  letter-spacing: -0.01em;
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: var(--card);
  border-right: 1px solid var(--line);
}

/* Buttons */
.stButton > button,
.stDownloadButton > button {
  background: var(--navy);
  border: 0;
  border-radius: 12px;
  min-height: 44px;
  padding: 0 24px;
  font-weight: 700;
}

.stButton > button p,
.stDownloadButton > button p {
  color: #FFFFFF;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
  background: #1B3F63;
}

.stButton > button:disabled,
.stDownloadButton > button:disabled {
  opacity: 0.45;
}

/* Inputs */
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="textarea"] {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
}

div[data-baseweb="input"] > div:focus-within {
  border-color: var(--sage);
}

/* Tabs */
button[data-baseweb="tab"] {
  font-weight: 600;
  color: var(--muted);
}

button[data-baseweb="tab"][aria-selected="true"] {
  color: var(--navy);
}

div[data-baseweb="tab-highlight"] {
  background-color: var(--sage);
}

/* Tables, expanders and alerts */
[data-testid="stDataFrame"] {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow: hidden;
}

[data-testid="stExpander"] {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 16px;
}

[data-testid="stAlert"] {
  background: var(--card);
  color: var(--navy);
  border: 1px solid var(--line);
  border-radius: 12px;
}

/* Top navigation */
div[data-testid="stRadio"] > div[role="radiogroup"] {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: fit-content;
  max-width: 100%;
  margin: 12px auto 30px auto;
  padding: 7px 12px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: 0 2px 8px rgba(16, 40, 63, 0.04);
}

div[data-testid="stRadio"] label {
  margin: 0;
  padding: 7px 16px;
  border-radius: 10px;
  cursor: pointer;
  color: var(--muted);
  font-size: 14px;
  font-weight: 700;
  transition: background 0.2s ease, color 0.2s ease;
}

div[data-testid="stRadio"] label:hover {
  background: var(--sage-light);
  color: var(--navy);
}

div[data-testid="stRadio"] label:has(input:checked) {
  background: var(--sage);
  color: #FFFFFF;
}

div[data-testid="stRadio"] label:has(input:checked) p,
div[data-testid="stRadio"] label:has(input:checked) div {
  color: #FFFFFF;
}

@media (max-width: 600px) {
  div[data-testid="stRadio"] > div[role="radiogroup"] {
    width: 100%;
    gap: 2px;
    padding: 5px;
  }

  div[data-testid="stRadio"] label {
    padding: 7px 10px;
    font-size: 12px;
  }
}

/* Dashboard metrics */
[data-testid="stMetric"] {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px;
}

[data-testid="stMetricLabel"] {
  color: var(--muted);
}

[data-testid="stMetricValue"] {
  color: var(--navy);
}

/* Altair chart cards */
[data-testid="stVegaLiteChart"] {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 10px;
  box-shadow: 0 2px 8px rgba(16, 40, 63, 0.035);
}

footer {
  visibility: hidden;
}
</style>
"""

def apply_style():
    """Apply the shared Class Mind styling."""
    st.markdown(CSS, unsafe_allow_html=True)
