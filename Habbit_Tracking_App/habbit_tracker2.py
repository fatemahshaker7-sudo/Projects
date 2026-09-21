import streamlit as st
from IPython.display import JSON
import numpy as np
import pandas as pd
import altair as alt
import datetime
import os
import requests
from dotenv import load_dotenv
from openai import OpenAI

file_path = "habits.csv"

"""
        This file contains all the functions used for Habit Traker App
        """

def load_file(file_path):

    """
        This function loads the file to read the user data from it
        """
    df = pd.read_csv(file_path)
    df["StartDateTime"]= pd.to_datetime(df["StartDateTime"] , format = "mixed")
    return df


def save_habit(habbit,category,target,start_date_time,frequency):
    """
            This function saves the user data as a data frame and changing the time format and saves it in 
            csv file, if not exist it will make one
            """
    new_row = pd.DataFrame([{
        "Habit": habbit,
        "Category": category,
        "Target": target,
        "StartDateTime": pd.Timestamp(start_date_time).strftime("%Y-%m-%d %H:%M:%S"),
        "Frequency": frequency
        }])

    if not os.path.exists(file_path):
        new_row.to_csv(file_path,index=False)
    else:
        new_row.to_csv(file_path,mode='a',header=False, index=False)
    # end def


def edited_table(sub_df):
            """
            This function is to make a editable table , were deleting any row is possible by selecting it 
            and changing any value is also possible
                """
            edited_df = st.data_editor(sub_df, num_rows="dynamic",hide_index=True,
                        column_config={
                        "Frequency": st.column_config.SelectboxColumn(
                        "Frequency", help="The habbit frequency",width="medium",
                        options=[
                        "Daily",
                        "Weekly",
                        "Monthly",],required=True,), "StartDateTime": st.column_config.DatetimeColumn(
                        "StartDateTime",
                        min_value=datetime.datetime(2026, 9, 1),
                        max_value=datetime.datetime(2027, 1, 1),
                        format="D MMM YYYY, h:mm a",step=60,),},key="edit_table",)
            return edited_df 
            
        # end def    

def get_period(dates,freq):
    """
        This function rounds the Datetime according to the frequency selected 
        """
    if freq == "Daily":
        return dates.dt.floor("D")
    elif freq == "Weekly":
        return dates.dt.to_period("W")
    elif freq == "Monthly":
        return dates.dt.to_period("M")

def compute_streak(dates,freq):
    """
        This function takes the dates the user logged in and the frequecy the user registered for it to 
        spot streaks. 
        """
    periods = get_period(dates,freq)
    if freq =="Daily":
        sorted_date = sorted(periods.unique())
        datess = pd.Series(sorted_date)
        gaps = datess.diff().dt.days
    else:
        sorted_periods = pd.Series(sorted(p.ordinal for p in periods.unique()))
        gaps = sorted_periods.diff()
    if len(gaps)==0:
        return 0
    # if the user missed one day the streak is gone
    is_consecutive = gaps ==1
    streak_1 = (~is_consecutive).cumsum()
    longest = is_consecutive.groupby(streak_1).sum().max()
    return int(longest)+1


def log_required(dates,freq, today):
    """
        This function takes the dates the user logged in and the frequecy the user registered for each habit 
        and takes todays date into account to know what habbit is due today and was last logged 
            """
    last_logged = dates.max()
    # Period('2026-09', 'M')
    if freq =="Daily":
        return last_logged.to_period("D") != today.to_period("D")
    elif freq == "Weekly":
        return last_logged.to_period("W") != today.to_period("W")
    elif freq =="Monthly":
        return last_logged.to_period("M") != today.to_period("M")

def unique_habbits_extract(habbit_df):
        """
        extracts the information of each habbit  
        """
        streak_results = []
        habit_info = {}
        for habit , habit_rows in habbit_df.groupby("Habit", sort=False):
            freq = habit_rows["Frequency"].iloc[0]
            dates = habit_rows["StartDateTime"]
            habit_info[habit] = (freq,dates)
            habit_streak = compute_streak(dates,freq)
            if habit_streak > 2:
                streak_results.append((habit,habit_streak))
        return (streak_results,habit_info)
    # end def

def Motivation_quote():
    """
    API link to zenquotes website to print motivational quotes
    """
    
    response = requests.get("https://zenquotes.io/api/random")
    quote = response.json()[0]["q"]
    Motivation_badge = st.badge(f"{quote}", icon="🌟", color="violet") 
    
    return Motivation_badge
# end def


def get_llm_response(prompt):
    """
        LLM model API ,where the LLM is defined to be a personal habit coach and to suggest habbit pairing
        spot burnout,etc. 
        """
    #try:
    load_dotenv('OpenAi_KEY.env')
    open_api_key = os.getenv('OpenAi_KEY')
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key= open_api_key ,)
    # First API call with reasoning
    response = client.chat.completions.create(
    model="nvidia/nemotron-3-ultra-550b-a55b:free",
    messages=[
          {
            "role": "system",
            "content": "You are a personal habbit coach, that takes the completion logs and streaks about the user's habbits to generate personalized advice, spot burn out patterns and suggest habbit stack in the form After I exsisting habit, I will new related habbit , should be in short and no more than 4 sentences "
          },
          {
            "role": "user",
            "content": (prompt)
          },
        ],
        max_tokens = 2000,
        extra_body={"reasoning": {"enabled": True}})

    # Extract the assistant message with reasoning_details
    message = (response.choices[0].message).content
    
    return message
    