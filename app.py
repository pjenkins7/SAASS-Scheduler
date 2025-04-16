# app.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime
from scheduler import run_scheduler

st.set_page_config(page_title="SAASS Scheduler", layout="wide")
st.title("SAASS Scheduler (NEOS-Backed Optimization)")
# ---------------------------------------------------------
# 📝 Instructions and CSV guidance
st.markdown("""
Welcome to the **SAASS Scheduler**.

This tool assigns students to balanced course groups using optimization submitted to the [NEOS Server](https://neos-server.org).

---

### 📥 What You'll Need

Upload a `.csv` file with the following **two columns**, with these exact headers:

| Student Name | AFSC |
|--------------|------|
| Jenkins-P    | 15A  |
| Brown-D      | 21A  |
| Taylor-J     | Civ  |
| Jones-P      | Army |
| Carter-X     | Marine |

---

### ⚠️ Formatting Guidelines (Important)

- ✅ **Student Name** must follow the format: `LastName-FirstInitial` (no spaces).
- ✅ **AFSC** must be labeled **consistently**:
  - If the student is **not** from the Air Force, use an appropriate identifier. For example: `"Marine"`, `"Army"`, or `"Civ"` (case-sensitive, spelled exactly).
  - Use consistent formatting for all AFSCs or job titles. For example, if you use `"15A"`, apply that format universally. Do **not** mix variants like `"15-A"`, `"15a"`, or `"Ops Research"`.
- 🚫 Do **not** include extra columns or leave blank rows.
- ✅ An **email address is required**, as the NEOS server uses it to process the optimization job.

🧠 **Why it matters:**  
The optimization model enforces a constraint that **no more than two members with the same AFSC or job title** can be assigned to a single group. Inconsistent or misspelled entries will bypass this constraint and reduce solution quality.
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
email = st.text_input("Enter your NEOS email address:")
uploaded_file = st.file_uploader("Upload the SAASS student roster CSV", type=["csv"])

# ✅ Session state init
if "opt_run" not in st.session_state:
    st.session_state.opt_run = False
if "uploaded" not in st.session_state:
    st.session_state.uploaded = None

# ✅ Store uploaded file in session to allow reset
if uploaded_file:
    st.session_state.uploaded = uploaded_file

# ✅ Buttons in a row
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("🚀 Start Optimization"):
        st.session_state.opt_run = True

with col2:
    if st.button("🔄 Reset App"):
        st.session_state.opt_run = False
        st.session_state.uploaded = None
        st.experimental_rerun()

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

            # Generate unique timestamped output name
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            output_filename = f"AY26_Scheduler_{timestamp}.xlsx"

            # Run the scheduler
            output_file, _ = run_scheduler(
                df,
                email,
                progress_callback=show_step,
                progress_bar=progress_bar
            )

            # Rename to timestamped output
            os.rename("AY26_Scheduler_Summary.xlsx", output_filename)

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
