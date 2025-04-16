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

This tool assigns students to balanced course groups using optimization submitted to the [NEOS Server](https://neos-server.org). It maximizes interaction diversity while ensuring no more than two students with the same AFSC/job title appear in the same group.

---

### 📥 What You'll Need

Upload a `.csv` file with the following **two columns**, with these exact headers:

| Student Name | AFSC |
|--------------|------|
| Jenkins-P    | 15A  |
| Smith-J      | 11F  |
| Brown-M      | Marine |
| Taylor-A     | Civ  |
| Carter-B     | Army |

---

### ⚠️ Formatting Guidelines (Important)

- ✅ **Student Name** must follow the format: `LastName-FirstInitial` (no spaces)
- ✅ **AFSC/Job Titles** must be labeled **consistently**
  - Use `"Marine"`, `"Army"`, or `"Civ"` (exact spelling and capitalization)
  - Do not use abbreviations like `"civilian"` or `"mar"` — they must match exactly
- 🚫 Do **not** include extra columns (e.g., `Student Number`) or blank rows
- ✅ You must enter your **email address**, which is required for NEOS job submission

🧠 **Why it matters:**  
The optimization model limits each group to **no more than 2 members with the same AFSC/job title**. Inconsistent spelling will lead to incorrect constraints.

---

### 📄 Download a Sample CSV File

Click below to download a sample roster for reference or testing:

👉 [Download `sample_roster.csv`](https://raw.githubusercontent.com/pjenkins7/SAASS-Scheduler/main/sample_roster.csv)
""")

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
