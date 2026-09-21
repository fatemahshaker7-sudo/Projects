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
import habbit_tracker2 as ht

file_path = "habits.csv"

def main():
    """
    This function contains all the functionalities of each page when selected
    """
    st.title(":red[Habit Tracker]")
    menu = ["Add New", "Log Completion", "Streaks & Statistics","Edit"]
    choice = st.sidebar.selectbox("Menu",menu)
    # side bar functionalities
    if choice == "Add New":
        st.subheader("Add Habbit")

        # Layout
        col1,col2 = st.columns(2)
        with col1:
            habbit = st.text_area("What is your new habbit")
            category = st.selectbox("Choese a Category", ["Health", "Productivity", "Learning"])
            target = st.text_area("Your Target")
        with col2:
            start_date_time = st.datetime_input("Habit Start Date and Time",datetime.datetime(2026, 9, 1, 16, 45),)
            frequency = st.radio("Frequency", ["Daily", "Weekly", "Monthly"])

        if st.button("Add Habit"):
            ht.save_habit(habbit,category,target,start_date_time,frequency)
            st.badge(f"{habbit} scheduled from {start_date_time}", icon="📅", color="green")
            st.badge(f"For {frequency} bases", icon="🔁", color="blue")

    elif choice == "Log Completion":
        st.subheader("Log Completion")
        # Lodding the data
        habbit_df = ht.load_file(file_path)
        # Showing the optimal time for each habbit
        habbit_df["Optimal Time"] = habbit_df["StartDateTime"] - habbit_df["StartDateTime"].dt.normalize()
        avg_habbit_time = habbit_df.groupby("Habit")["Optimal Time"].mean()
        st.write(pd.to_datetime(avg_habbit_time.dt.total_seconds(), unit="s").dt.time)
        
        now = pd.Timestamp.now()
        habits_due = []
        habbit_done = []

        [streak_results,habit_info] = ht.unique_habbits_extract(habbit_df)
            
        #checks which habbits are due today and Shows notifications for them 
        for habit, (freq,dates) in habit_info.items():
            if ht.log_required(dates,freq, now.floor("D")):
                habits_due.append(habit)
            

        # shows the habbits in check boxes list    
        if habits_due:
            st.write("Which habit was completed:")
            
            for habit in habits_due:
                st.toast(f'{habit} is due today')
                if st.checkbox(habit, value = False ):
                    habbit_done.append(habit)
            
        # prints a new row in the csv file when the habbit is checked logged
        if st.button("Completed"):
            for habit in habbit_done:
                habit_new_row = habbit_df[habbit_df["Habit"] == habit].iloc[0]
                ht.save_habit(habit_new_row["Habit"],habit_new_row["Category"],habit_new_row["Target"], now, habit_new_row["Frequency"])
                st.badge(f"{habit} completed on {now}", icon="✔", color="green")
                ht.Motivation_quote()
                

    elif choice == "Streaks & Statistics":
        st.subheader("Streaks & Statistics")
        # Loads the data
        habbit_df = ht.load_file(file_path)
        
        [streak_results,habit_info] = ht.unique_habbits_extract(habbit_df)
        unique_habits = list(habit_info)

        # Streak metrics with progress bar on it
        if streak_results:
            ht.Motivation_quote()
            
            cols = st.columns(len(streak_results))
            for col, (habit,streak) in zip (cols,streak_results):
                with col.container(border=True):
                    col.metric(label = habit, value = streak , delta="🔥")
                    st.progress(min(streak,30), text = f"{(min(streak,30)/30)*100}%")
            st.write(ht.get_llm_response(f"{habit}: {streak}-day streak, {(min(streak,30)/30)*100} last 30 days."))
                    
                    
        # Calande views
        selected = st.selectbox("choose a habbit",unique_habits)
        filtered_selection = habbit_df[habbit_df["Habit"] == selected]

        # Timestamp('2026-09-21 00:00:00')
        filtered_selection["date"] = filtered_selection["StartDateTime"].dt.floor("D") 

        daily_counts = filtered_selection.groupby("date").size().reset_index(name="count")
        day_order = ["Sat","Sun", "Mon", "Tue" , "Wed", "Thu", "Fri"]
        chart = (alt.Chart(daily_counts).mark_rect().encode(x="week(date):O", y=alt.Y("day(date):O", sort=day_order), 
                color="count:Q", tooltip = ["date:T", "count:Q"],).properties(width = alt.Step(20), height=alt.Step(20)))
        st.altair_chart(chart)  

    elif choice == "Edit":
        st.subheader("Edit or Remove a Habbit")
        # Loads the data
        habbit_df = ht.load_file(file_path)
        unique_habits = habbit_df["Habit"].unique()
        selected = st.selectbox("Choose a habbit to modify",unique_habits)
        sub_df = habbit_df[habbit_df["Habit"] == selected].reset_index(drop=True)
        edited_df = ht.edited_table(sub_df)
        if st.button("Save Changes"):
            remaining_df = habbit_df[habbit_df["Habit"] != selected]
            full_df = pd.concat([remaining_df,edited_df], ignore_index=True)
            full_df.to_csv(file_path, index = False)
            st.session_state.edit_target = None
            st.badge(f"Changed Succesfully", icon="✅", color="green")
        
# end def



if __name__=='__main__':
    main()
