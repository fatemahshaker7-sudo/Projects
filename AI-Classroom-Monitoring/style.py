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
}

/* page and fonts */
.stApp { background: var(--bg); color: var(--navy); }
.stApp, .stApp p, .stApp label, .stApp li, .stApp button, .stApp input, .stApp textarea {
  font-family: 'Source Sans 3', sans-serif;
}
h1, h2, h3, h4 {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  color: var(--navy);
  font-weight: 700;
  letter-spacing: -0.01em;
}

/* sidebar */
[data-testid="stSidebar"] { background: var(--card); border-right: 1px solid var(--line); }

/* buttons */
.stButton > button, .stDownloadButton > button {
  background: var(--navy);
  border: 0;
  border-radius: 12px;
  min-height: 44px;
  padding: 0 24px;
  font-weight: 700;
}
.stButton > button p, .stDownloadButton > button p { color: #FFFFFF; }
.stButton > button:hover, .stDownloadButton > button:hover { background: #1B3F63; }
.stButton > button:disabled, .stDownloadButton > button:disabled { opacity: 0.45; }

/* inputs */
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
}
div[data-baseweb="input"] > div:focus-within { border-color: var(--sage); }

/* tabs */
button[data-baseweb="tab"] { font-weight: 600; color: var(--muted); }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--navy); }
div[data-baseweb="tab-highlight"] { background-color: var(--sage); }

/* cards: tables, expanders, messages */
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

footer { visibility: hidden; }
</style>
"""

def apply_style():
    st.markdown(CSS, unsafe_allow_html=True)
