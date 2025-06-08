import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
from scheduler import run_scheduler_single_course

st.set_page_config(page_title="SAASS Scheduler", layout="wide")
st.title("SAASS Scheduler (NEOS-Backed Optimization)")

# ---------------------------------------------------------
# 📘 Full Instructions and CSV Guidance
st.markdown("""
Welcome to the **SAASS Scheduler**.

This tool assigns students to balanced course groups using optimization submitted to the [NEOS Server](https://neos-server.org).

---

### 🗂️ Required Roster CSV (All Users)

Upload a `.csv` file with exactly **two columns**:

| Student Name | Job Type |
|--------------|----------|
| Jenkins-P    | 15A      |
| Brown-D      | 21A      |
| Taylor-J     | Civ      |

#### Roster Formatting Rules:
- `Student Name` format must be `LastName-FirstInitial` (no spaces).
- `Job Type` must be consistent (e.g., always use `"15A"`, not `"15-A"` or `"15a"`).
- Use `"Marine"`, `"Army"`, or `"Civ"` for non-Air Force roles.
- ❌ Do **not** include extra columns or blank rows.
- ✅ An email is required to submit jobs to NEOS.

---

### 📘 Optional Prior Grouping CSV (for Interaction Awareness)

If prior courses have been completed, upload a CSV with **previous groupings** to guide the model’s interaction penalties.

| Course | Group | Student     |
|--------|-------|-------------|
| 1      | 1     | Jenkins-P   |
| 1      | 1     | Brown-D     |
| 1      | 2     | Taylor-J    |

#### Prior CSV Formatting Rules:
- `Course`: Integer (e.g., 1, 2, 3)
- `Group`: Group number for that course (starts at 1)
- `Student`: Must match roster names exactly

💡 A mismatch in student names will cause that record to be ignored.
""")

# Optional sample download
if os.path.exists("sample_roster.csv"):
    with open("sample_roster.csv", "rb") as f:
        st.download_button("Download Example Roster CSV", f, file_name="sample_roster.csv")

if os.path.exists("sample_prior_assignments.csv"):
    with open("sample_prior_assignments.csv", "rb") as f:
        st.download_button("Download Example Prior Grouping CSV", f, file_name="sample_prior_assignments.csv")

# Upload roster
uploaded_roster = st.file_uploader("Upload Roster CSV", type=["csv"])

student_names = []
job_types = []
num_students = 0
if uploaded_roster:
    df_roster = pd.read_csv(uploaded_roster)
    if "Student Name" in df_roster.columns and "Job Type" in df_roster.columns:
        student_names = df_roster["Student Name"].tolist()
        job_types = df_roster["Job Type"].tolist()
        num_students = len(student_names)
        st.success(f"{num_students} students loaded.")
    else:
        st.error("CSV must include 'Student Name' and 'Job Type' columns.")

# Group sizes
if num_students > 0:
    num_groups = st.number_input("How many groups to form?", min_value=2, max_value=20, value=4)
    recommended = [num_students // num_groups + (1 if i < num_students % num_groups else 0) for i in range(num_groups)]
    st.markdown("### Group Sizes (editable)")
    group_sizes_input = []
    total_assigned = 0
    cols = st.columns(num_groups)
    for i in range(num_groups):
        with cols[i]:
            val = st.number_input(f"Group {i + 1}", min_value=1, max_value=num_students, value=recommended[i], key=f"gsize_{i}")
            group_sizes_input.append(val)
            total_assigned += val
    if total_assigned != num_students:
        st.warning(f"Group sizes sum to {total_assigned}, but roster has {num_students} students.")

# Upload prior grouping
prior_csv = st.file_uploader("Upload Prior Grouping CSV", type=["csv"])
interaction_matrix = None
prior_df = None
suggested_course = 1
if num_students > 0:
    name_to_index = {name: i for i, name in enumerate(student_names)}
    interaction_matrix = np.zeros((num_students, num_students), dtype=int)
    if prior_csv:
        df_prior = pd.read_csv(prior_csv)
        prior_df = df_prior
        if {"Course", "Group", "Student"}.issubset(df_prior.columns):
            suggested_course = df_prior["Course"].max() + 1
            for (_, _), group in df_prior.groupby(["Course", "Group"]):
                students = group["Student"].tolist()
                for i in range(len(students)):
                    for j in range(i + 1, len(students)):
                        a, b = name_to_index.get(students[i]), name_to_index.get(students[j])
                        if a is not None and b is not None:
                            interaction_matrix[a, b] += 1
                            interaction_matrix[b, a] += 1
        else:
            st.error("Prior grouping CSV must include columns: Course, Group, Student")

# Optimization parameters
st.markdown("### Optimization Settings")
email = st.text_input("Email (required for NEOS)")
course_number = st.number_input("Course number to assign", min_value=1, value=suggested_course)
job_type_limit = st.number_input("Max per job type per group", min_value=1, value=2)
penalty_threshold = st.number_input("Penalty threshold (interactions)", min_value=1, value=3)
max_interaction = st.number_input("Max allowed interactions", min_value=1, value=4)
time_limit = st.number_input("Solver time limit (seconds)", min_value=10, max_value=3600, value=600)

# Run optimization
if st.button("Run Optimization") and email and uploaded_roster and num_students > 0:
    if total_assigned != num_students:
        st.error("Group sizes must add up to number of students.")
    else:
        try:
            with st.status("Running optimization...") as status:
                def show_step(msg):
                    st.write(msg)
                progress_bar = st.progress(0.0)
                timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
                output_filename = f"SAASS_Scheduler_{course_number}_{timestamp}.xlsx"

                new_assignments, all_assignments = run_scheduler_single_course(
                    df=pd.DataFrame({"Student Name": student_names, "Job Type": job_types}),
                    course_num=course_number,
                    email=email,
                    group_sizes=group_sizes_input,
                    interaction_matrix=interaction_matrix,
                    job_type_limit=job_type_limit,
                    penalty_threshold=penalty_threshold,
                    max_interaction=max_interaction,
                    time_limit=time_limit,
                    progress_callback=show_step,
                    progress_bar=progress_bar,
                    output_filename=output_filename,
                    prior_assignment_df=prior_df,
                    return_assignments_only=True
                )

                all_assignments.to_excel(output_filename, index=False)
                status.update(label="Optimization complete", state="complete")

            st.success("Download your results below:")
            with open(output_filename, "rb") as f:
                st.download_button("Download Excel Summary", f, file_name=output_filename)

            st.markdown("### New Groupings")
            for gnum in sorted(new_assignments["Group"].unique()):
                st.markdown(f"**Group {gnum}**")
                st.dataframe(new_assignments[new_assignments["Group"] == gnum][["Student"]].reset_index(drop=True))

        except Exception as e:
            st.error(f"Error occurred: {e}")
