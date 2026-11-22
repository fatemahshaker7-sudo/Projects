"""Academic Clean Green theme for ClassMind (Streamlit)."""
import streamlit as st


def apply_style():
    """Apply the Academic Clean Green theme across the Streamlit app."""
    st.markdown(
        """
        <style>
        /* Theme palette: soft white, sage, forest green */
        :root {
            --cm-bg: #F7F9F7;
            --cm-sage: #E8F0E9;
            --cm-border: #DCE7DE;
            --cm-green: #527A61;
            --cm-deep: #284C38;
            --cm-text: #26352B;
            --cm-muted: #68766D;
            --cm-mint: #E2F2E8;
        }

        .stApp {
            background: var(--cm-bg);
            color: var(--cm-text);
        }

        /* Main page spacing and width */
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2.5rem;
            max-width: 1500px;
        }


        /* Sidebar */
        [data-testid="stSidebar"] {
            background: var(--cm-sage);
            border-right: 1px solid var(--cm-border);
        }
        [data-testid="stSidebar"] * {
            color: var(--cm-deep);
        }
        [data-testid="stSidebar"] .stRadio label {
            font-weight: 500;
        }

        /* Headings and text */
        h1, h2, h3 {
            color: var(--cm-deep) !important;
            letter-spacing: -0.02em;
        }
        p, label, [data-testid="stMarkdownContainer"] {
            color: var(--cm-text);
        }
        small, .stCaption {
            color: var(--cm-muted) !important;
        }

        /* Buttons */
        .stButton > button, .stDownloadButton > button {
            background: var(--cm-green);
            color: #FFFFFF;
            border: 1px solid var(--cm-green);
            border-radius: 10px;
            padding: 0.48rem 1rem;
            font-weight: 600;
            transition: background 150ms ease, border-color 150ms ease, transform 150ms ease;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            background: var(--cm-deep);
            border-color: var(--cm-deep);
            color: #FFFFFF;
            transform: translateY(-1px);
        }
        .stButton > button:focus, .stDownloadButton > button:focus {
            box-shadow: 0 0 0 3px rgba(82, 122, 97, 0.22);
        }

        /* Cards, metrics, and bordered containers */
        [data-testid="stMetric"], [data-testid="stMetricContainer"] {
            background: #FFFFFF;
            border: 1px solid var(--cm-border);
            border-radius: 14px;
            padding: 0.85rem 1rem;
        }
        [data-testid="stMetricLabel"] {
            color: var(--cm-muted) !important;
        }
        [data-testid="stMetricValue"] {
            color: var(--cm-deep) !important;
            font-weight: 700;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--cm-border) !important;
            border-radius: 14px;
        }

        /* Tabs */
        [data-testid="stTabs"] button[role="tab"] {
            color: var(--cm-muted);
            font-weight: 600;
        }
        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            color: var(--cm-deep) !important;
        }
        [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            background-color: var(--cm-green) !important;
        }

        /* Inputs */
        input, textarea, [data-baseweb="select"] {
            border-radius: 9px !important;
        }
        [data-testid="stTextInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus,
        [data-testid="stNumberInput"] input:focus {
            border-color: var(--cm-green) !important;
            box-shadow: 0 0 0 2px rgba(82, 122, 97, 0.15) !important;
        }

        /* Tables and dataframe containers */
        [data-testid="stDataFrame"], [data-testid="stTable"] {
            border: 1px solid var(--cm-border);
            border-radius: 10px;
            overflow: hidden;
        }

        /* Expanders */
        [data-testid="stExpander"] {
            border: 1px solid var(--cm-border);
            border-radius: 12px;
            background: #FFFFFF;
        }

        /* Alerts: softer edges */
        [data-testid="stAlert"] {
            border-radius: 10px;
        }

        /* Links */
        a {
            color: var(--cm-green) !important;
        }
        a:hover {
            color: var(--cm-deep) !important;
        }

        /* Keep text readable in dark mode if user/system setting changes */
        @media (prefers-color-scheme: dark) {
            .stApp { background: var(--cm-bg); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
