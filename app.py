# app.py
import streamlit as st
import pandas as pd
import os
from scheduler import run_scheduler

st.set_page_config(page_title="SAASS Scheduler", layout="wide")
st.title("SAASS Scheduler (NEOS-Backed Optimization)")

# Step 1: Ask for email
email = st.text_input("Enter your NEOS email address:")

# Step 2: Upload CSV
uploaded_file = st.file_uploader("Upload the SAASS student roster CSV", type=["csv"])

# Step 3: Submit and run
if email and uploaded_file:
    st.info("Running optimization — this may take a minute...")
    
    try:
        df = pd.read_csv(uploaded_file)
        output_file = run_scheduler(df, email)

        st.success("Done! Download and review your outputs below:")

        # Excel file download
        with open(output_file, "rb") as f:
            st.download_button("Download Excel Summary", f, file_name=output_file)

        # Display heatmaps and bar charts for 3 example courses
        for course in [601, 600, 627]:
            heatmap = f"Heatmap_Course{course}.png"
            barchart = f"InteractionBar_Course{course}.png"
            if os.path.exists(heatmap):
                st.image(heatmap, caption=f"Heatmap – Course {course}", use_column_width=True)
            if os.path.exists(barchart):
                st.image(barchart, caption=f"Interaction Summary – Course {course}", use_column_width=True)

    except Exception as e:
        st.error(f"Something went wrong: {str(e)}")
