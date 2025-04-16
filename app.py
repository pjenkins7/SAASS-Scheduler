# app.py
import streamlit as st
import pandas as pd
import os
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

**Why it matters:**  
The optimization model enforces a constraint that **no more than two members with the same AFSC or job title** can be assigned to a single group. Inconsistent or misspelled entries will bypass this constraint and reduce solution quality.
""")

# ✅ Show download button for sample CSV
if os.path.exists("sample_roster.csv"):
    with open("sample_roster.csv", "rb") as f:
        st.download_button(
            label="📥 Download Example CSV File",
            data=f,
            file_name="sample_roster.csv",
            mime="text/csv"
        )

# ---------------------------------------------------------
# Step 1: Ask for email
email = st.text_input("Enter your NEOS email address:")

# Step 2: Upload CSV
uploaded_file = st.file_uploader("Upload the SAASS student roster CSV", type=["csv"])

# ---------------------------------------------------------
# Step 3: Submit and run
if email and uploaded_file:
    st.info("Running optimization — this may take a minute...")

    try:
        df = pd.read_csv(uploaded_file)
        output_file = run_scheduler(df, email)

        st.success("✅ Optimization complete! Download your outputs below:")

        with open(output_file, "rb") as f:
            st.download_button("📊 Download Excel Summary", f, file_name=output_file)

        for course in [601, 600, 627]:
            heatmap = f"Heatmap_Course{course}.png"
            barchart = f"InteractionBar_Course{course}.png"
            if os.path.exists(heatmap):
                st.image(heatmap, caption=f"Heatmap – Course {course}", use_column_width=True)
            if os.path.exists(barchart):
                st.image(barchart, caption=f"Interaction Summary – Course {course}", use_column_width=True)

    except Exception as e:
        st.error(f"Something went wrong: {str(e)}")
