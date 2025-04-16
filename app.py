# app.py
import streamlit as st
import pandas as pd
import os
from scheduler import run_scheduler

st.set_page_config(page_title="SAASS Scheduler", layout="wide")
st.title("SAASS Scheduler (NEOS-Backed Optimization)")

# Sample download
if os.path.exists("sample_roster.csv"):
    with open("sample_roster.csv", "rb") as f:
        st.download_button(
            label="📥 Download Example CSV File",
            data=f,
            file_name="sample_roster.csv",
            mime="text/csv"
        )

email = st.text_input("Enter your NEOS email address:")
uploaded_file = st.file_uploader("Upload the SAASS student roster CSV", type=["csv"])

if email and uploaded_file:
    try:
        with st.status("Running optimization...", expanded=True) as status:
            def show_step(msg):
                st.write(msg)

            st.write("📄 Reading uploaded CSV...")
            df = pd.read_csv(uploaded_file)

            st.write("📡 Submitting job to NEOS server...")
            progress_bar = st.progress(0.0)

            output_file, solved_courses = run_scheduler(
                df,
                email,
                progress_callback=show_step,
                progress_bar=progress_bar
            )

            status.update(label="✅ Optimization complete!", state="complete")

        st.success("✅ Optimization complete! Download your results below:")

        with open(output_file, "rb") as f:
            st.download_button("📊 Download Excel Summary", f, file_name=output_file)

        if os.path.exists("Heatmap_Final.png"):
            st.image("Heatmap_Final.png", caption="Final Interaction Matrix", use_column_width=True)
        if os.path.exists("InteractionBar_Final.png"):
            st.image("InteractionBar_Final.png", caption="Total Distinct Pairings per Student", use_column_width=True)

    except Exception as e:
        st.error(f"Something went wrong: {str(e)}")
