import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
from scheduler import run_scheduler_single_course

st.set_page_config(page_title="SAASS Scheduler", layout="wide")
st.title("SAASS Scheduler (NEOS-Backed Optimization)")

# -----------------------------------------------
# 📄 File upload and student count
uploaded_roster = st.file_uploader("📋 Upload the student roster CSV (Student Name, Job Type)", type=["csv"])
num_students = st.number_input("👥 Total number of students", min_value=1, max_value=100, value=45)

# -----------------------------------------------
# 🧮 Group size selection
num_groups = st.number_input("🔢 How many groups do you want to form?", min_value=2, max_value=20, value=4)

# Recommended group sizes
recommended = [num_students // num_groups + (1 if i < num_students % num_groups else 0) for i in range(num_groups)]

st.markdown("### ✏️ Group Sizes (editable)")
group_sizes_input = []
override_warning = False
total_assigned = 0

cols = st.columns(num_groups)
for i in range(num_groups):
    with cols[i]:
        val = st.number_input(f"Group {i + 1}", min_value=1, max_value=num_students, value=recommended[i], key=f"gsize_{i}")
        group_sizes_input.append(val)
        total_assigned += val

if total_assigned != num_students:
    st.warning(f"⚠️ Total group sizes ({total_assigned}) do not match number of students ({num_students}).")

# -----------------------------------------------
# 📂 Upload previous assignments (for interaction matrix)
st.markdown("### 📂 Upload Prior Course Groupings (Optional)")
prior_csv = st.file_uploader("Upload prior course grouping CSV (Course, Group, Student)", type=["csv"])

interaction_matrix = None
student_names = []
job_types = []

# Process roster if available
if uploaded_roster:
    df_roster = pd.read_csv(uploaded_roster)
    if "Student Name" not in df_roster.columns or "Job Type" not in df_roster.columns:
        st.error("❌ CSV must include 'Student Name' and 'Job Type' columns.")
    else:
        student_names = df_roster["Student Name"].tolist()
        job_types = df_roster["Job Type"].tolist()

        name_to_index = {name: i for i, name in enumerate(student_names)}
        interaction_matrix = np.zeros((num_students, num_students), dtype=int)

        if prior_csv:
            df_prior = pd.read_csv(prior_csv)
            if not {"Course", "Group", "Student"}.issubset(df_prior.columns):
                st.error("❌ Prior grouping CSV must have columns: Course, Group, Student")
            else:
                grouped = df_prior.groupby(["Course", "Group"])
                for _, group in grouped:
                    students = group["Student"].tolist()
                    for i in range(len(students)):
                        for j in range(i + 1, len(students)):
                            si, sj = students[i], students[j]
                            if si in name_to_index and sj in name_to_index:
                                a, b = name_to_index[si], name_to_index[sj]
                                interaction_matrix[a, b] += 1
                                interaction_matrix[b, a] += 1
                            else:
                                st.warning(f"⚠️ Student '{si}' or '{sj}' in prior group not found in roster. Ignored.")

# -----------------------------------------------
# 🎛️ Model parameters
st.markdown("### ⚙️ Optimization Settings")
email = st.text_input("Enter your email (required for NEOS):")
course_number = st.number_input("Course number to assign (e.g., 600)", min_value=100, max_value=999, step=1, value=600)
job_type_limit = st.number_input("Max students per job type in each group:", min_value=1, max_value=10, value=2)
penalty_threshold = st.number_input("Penalty threshold (pairs beyond this will be penalized):", min_value=1, max_value=10, value=3)
max_interaction = st.number_input("Maximum allowed interactions between any student pair:", min_value=1, max_value=10, value=4)

# -----------------------------------------------
# 🚀 Trigger optimization
if st.button("🚀 Run Optimization") and email and uploaded_roster and len(group_sizes_input) == num_groups:
    if total_assigned != num_students:
        st.error("❌ Group sizes must add up to total number of students.")
    else:
        try:
            with st.status("Running optimization...", expanded=True) as status:
                def show_step(msg):
                    st.write(msg)

                st.write("📡 Submitting job to NEOS server...")
                progress_bar = st.progress(0.0)

                timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
                output_filename = f"SAASS_Scheduler_{course_number}_{timestamp}.xlsx"

                output_file = run_scheduler_single_course(
                    df=pd.DataFrame({"Student Name": student_names, "Job Type": job_types}),
                    course_num=course_number,
                    email=email,
                    group_sizes=group_sizes_input,
                    interaction_matrix=interaction_matrix,
                    job_type_limit=job_type_limit,
                    penalty_threshold=penalty_threshold,
                    max_interaction=max_interaction,
                    progress_callback=show_step,
                    progress_bar=progress_bar,
                    output_filename=output_filename
                )

                status.update(label="✅ Optimization complete!", state="complete")

            st.success("✅ Optimization complete! Download your results below:")
            with open(output_file, "rb") as f:
                st.download_button("📊 Download Excel Summary", f, file_name=output_filename)

        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")
