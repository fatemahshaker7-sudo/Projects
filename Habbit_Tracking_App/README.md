# 📅 Habit Tracker App 

[Streamlit_Habbit_Tracking_App](https://habbit-tracking-app.streamlit.app/)

A Streamlit web app for building and tracking daily, weekly, and monthly habits. Log completions, watch your streaks grow, view a calendar heatmap of your activity, and get short personalized coaching tips from an LLM.

---

## Features

| Page | What it does |
|------|--------------|
| **Add New** | Create a habit with a name, category (Health / Productivity / Learning), target, start date & time, and frequency (Daily / Weekly / Monthly). |
| **Log Completion** | Shows the average time of day you usually do each habit, pops up a notification for habits that are due, and lets you check them off. Every completion is saved with a timestamp and a random motivational quote is displayed. |
| **Streaks & Statistics** | Displays a metric card and a 30-day progress bar for every habit with a streak longer than 2 periods, an AI coach message, and a calendar-style heatmap (Altair) of completions for the habit you select. |
| **Edit** | Pick a habit in a dialog, then modify or delete it. Rows can be edited, added, or removed in an interactive table and saved back to the CSV. |

### How it works

- **Storage:** everything lives in a single `habits.csv` file. The first row for a habit is its creation; every completion you log appends a new row with the same habit details and the completion timestamp.
- **Streaks:** completion timestamps are grouped into periods (day, ISO week, or month according to the habit's frequency). The streak is the longest run of consecutive periods with at least one log.
- **Due habits:** a habit is "due" if its most recent log is not in the current day / week / month.
- **Motivation:** random quotes come from the free [ZenQuotes API](https://zenquotes.io/).
- **AI coach:** the app sends your habit name, streak length, and 30-day progress to an LLM through [OpenRouter](https://openrouter.ai/) (OpenAI-compatible API). The model is prompted to act as a habit coach, spot burnout patterns, and suggest habit stacking ("After I *existing habit*, I will *new habit*") in no more than 4 sentences.

---

## Project Structure

```
.
├── project1_HabbitTracker2.py              # Streamlit UI (the main() function and all pages)
├── habbit_tracker2.py   # Helper functions: file I/O, streaks, quotes, LLM call
├── habits.csv          # Your data (created automatically on first "Add Habit")
├── OpenAi_KEY.env      # Your OpenRouter API key (not committed)
└── requirements.txt
```



### `habits.csv` format

| Column | Example |
|--------|---------|
| `Habit` | `Drink water` |
| `Category` | `Health` |
| `Target` | `2 liters` |
| `StartDateTime` | `2026-09-01 16:45:00` |
| `Frequency` | `Daily` |

---

## Getting Started

### 1. Prerequisites

- Python 3.9+
- An [OpenRouter](https://openrouter.ai/) API key (only needed for the AI coach message)


**`requirements.txt`**

```
streamlit
pandas
numpy
altair
requests
python-dotenv
openai

```


Use a recent Streamlit release, since the app relies on newer widgets such as `st.datetime_input`, `st.badge`, and `st.dialog`.

### 3. Add your API key

Create a file named `OpenAi_KEY.env` in the project root:

```
OpenAi_KEY=your_openrouter_api_key_here
```

OpenAi_KEY.env
```

### 4. Run the app


Then open the URL Streamlit prints (usually http://localhost:8501).

---

## Usage

1. Go to **Add New**, fill in the form, and click **Add Habit**. This creates `habits.csv` if it doesn't exist yet.
2. Each day (or week / month, depending on frequency), open **Log Completion**, tick the habits you finished, and click **Completed**.
3. Open **Streaks & Statistics** to see your streaks, coach message, and heatmap.
4. Use **Edit** to fix mistakes, change a frequency, or delete a habit.

---

## Configuration

| Setting | Where | Default |
|---------|-------|---------|
| Data file path | `file_path` in both `app.py` and `habbit_tracker.py` | `habits.csv` |
| LLM model | `get_llm_response()` in `habbit_tracker.py` | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| API key file / variable | `load_dotenv(...)` / `os.getenv(...)` in `habbit_tracker.py` | `OpenAi_KEY.env` / `OpenAi_KEY` |
| Editable date range | `edited_table()` in `habbit_tracker.py` | 2026-09-01 to 2027-01-01 |
| Streak progress target | Progress bar in `app.py` | 30 periods |

---

## Known Limitations

- **AI coach scope:** the coach message is generated once from the last habit in the streak list, rather than one per habit.
- **Date limits:** the Edit table only accepts dates between 1 Sep 2026 and 1 Jan 2027, and the Add form defaults to 1 Sep 2026 at 16:45. Adjust these in the code for longer-term use.
- **First run:** the **Log Completion**, **Streaks & Statistics**, and **Edit** pages expect `habits.csv` to exist, so add at least one habit first.
- **Network access:** quotes (ZenQuotes) and the AI coach (OpenRouter) need an internet connection, and free tiers may be rate limited.

---

## Tech Stack

[Streamlit](https://streamlit.io/) · [pandas](https://pandas.pydata.org/) · [Altair](https://altair-viz.github.io/) · [OpenAI Python SDK](https://github.com/openai/openai-python) (via OpenRouter) · [ZenQuotes API](https://zenquotes.io/)

---

## License

no licence needed.
