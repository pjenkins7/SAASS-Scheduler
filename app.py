# app.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime
from scheduler import run_scheduler_single_course

st.set_page_config(page_title="SAASS Scheduler", layout="wide")
st.title("SAASS Scheduler (NEOS-Backed Optimization)")

# ---------------------------------------------------------
# 📝 Instructions and CSV guidance
st.markdown("""
Welcome to the **SAASS Scheduler**.

This tool assigns students to balanced course groups using optimization submitted to the [NEOS Server](https://neos-server.org).

---

### What You'll Need

Upload a `.csv` file with the following **two columns**, with these exact headers:

| Student Name | Job Type |
|--------------|----------|
| Jenkins-P    | 15A      |
| Brown-D      | 21A      |
| Taylor-J     | Civ      |
| Jones-P      | Army     |
| Carter-X     | Marine   |

---

### Formatting Guidelines (Important)

- **Student Name** must follow the format: `LastName-FirstInitial` (no spaces).
- **Job Type** must be labeled **consistently**:
  - Use `"Marine"`, `"Army"`, or `"Civ"` for non-Air Force students (case-sensitive).
  - Use consistent formatting for all AFSCs (e.g., `"15A"`, not `"15-A"` or `"Ops Research"`).
- Do **not** include extra columns or blank rows.
- A valid **email address is required**, as the NEOS server uses it to run the optimization.

---
""")

# ✅ Optional download: sample file
if os.path.exists("sample_roster.csv"):
    with open("sample_roster.csv", "rb") as f:
        st.download_button(
            label="📥 Download Example CSV File",
            data=f,
            file_name="sample_roster.csv",
            mime="text/csv"
        )

# ✅ Input fields
email = st.text_input("Enter a valid email address:")
uploaded_file = st.file_uploader("Upload the SAASS student roster CSV", type=["csv"])

course_number = st.number_input("Enter Course Number (e.g., 600):", min_value=100, max_value=999, step=1, value=600)
job_type_limit = st.number_input("Max students per job type in each group:", min_value=1, max_value=10, value=2)
penalty_threshold = st.number_input("Penalty threshold (pairs beyond this will be penalized):", min_value=1, max_value=10, value=3)
max_interaction = st.number_input("Maximum allowed interactions between any student pair:", min_value=1, max_value=10, value=4)

# ✅ Session state init
if "opt_run" not in st.session_state:
    st.session_state.opt_run = False
if "uploaded" not in st.session_state:
    st.session_state.uploaded = None

# ✅ Store uploaded file in session to allow reset
if uploaded_file:
    st.session_state.uploaded = uploaded_file

# ✅ Run-time Disclaimer
st.info("""
This version of the app solves **only one course at a time**.  
You can select which course to solve and customize interaction and job constraints above.  
Expected runtime: **1–10 minutes**, depending on NEOS server load.
""")

# ✅ Buttons in a row
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🚀 Start Optimization"):
        st.session_state.opt_run = True

# ✅ Run if ready and triggered
if email and st.session_state.uploaded and st.session_state.opt_run:
    try:
        with st.status("Running optimization...", expanded=True) as status:
            def show_step(msg):
                st.write(msg)

            st.write("📄 Reading uploaded CSV...")
            df = pd.read_csv(st.session_state.uploaded)

            st.write("📡 Submitting job to NEOS server...")
            progress_bar = st.progress(0.0)

            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            output_filename = f"SAASS_Scheduler_{course_number}_{timestamp}.xlsx"

            output_file = run_scheduler_single_course(
                df=df,
                course_num=course_number,
                email=email,
                job_type_limit=job_type_limit,
                penalty_threshold=penalty_threshold,
                max_interaction=max_interaction,
                progress_callback=show_step,
                progress_bar=progress_bar,
                output_filename=output_filename
            )

            status.update(label="✅ Optimization complete!", state="complete")
            st.session_state.opt_run = False

        st.success("✅ Optimization complete! Download your results below:")

        with open(output_filename, "rb") as f:
            st.download_button("📊 Download Excel Summary", f, file_name=output_filename)

        if os.path.exists("Heatmap_Final.png"):
            st.image("Heatmap_Final.png", caption="Final Interaction Matrix", use_container_width=True)
        if os.path.exists("InteractionBar_Final.png"):
            st.image("InteractionBar_Final.png", caption="Total Distinct Pairings per Student", use_container_width=True)

    except Exception as e:
        st.error(f"Something went wrong: {str(e)}")
        st.session_state.opt_run = False
