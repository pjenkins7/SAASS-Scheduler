import streamlit as st
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
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
- Do **not** include extra columns or blank rows.

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
prior_csv = st.file_uploader("Upload Prior Grouping CSV (optional)", type=["csv"])
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
penalty_weight = st.number_input("Penalty weight (penalty per repeat interaction after penalty threshold)", min_value=0.0, value=0.25, step=0.1)
max_interaction = st.number_input("Max allowed interactions", min_value=1, value=4)
time_limit = st.number_input("Solver time limit (seconds)", min_value=10, max_value=3600, value=30)

# Warn user if required inputs are missing
if not email:
    st.warning("⚠️ Please enter a valid email to proceed with optimization.")

if not uploaded_roster:
    st.warning("⚠️ Please upload a valid roster CSV file.")

if num_students == 0:
    st.warning("⚠️ No students loaded from roster. Ensure your CSV has the correct format.")


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
                    penalty_weight=penalty_weight,
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

                # Save results for persistent rendering
                st.session_state["all_assignments"] = all_assignments
                st.session_state["new_assignments"] = new_assignments
                st.session_state["output_filename"] = output_filename

        except Exception as e:
            st.error(f"Error occurred: {e}")
# ✅ Display results if available in session state
if "all_assignments" in st.session_state and "new_assignments" in st.session_state:
    all_assignments = st.session_state["all_assignments"]
    new_assignments = st.session_state["new_assignments"]
    output_filename = st.session_state["output_filename"]

    st.success("Download your results below:")
    with open(output_filename, "rb") as f:
        st.download_button("Download Excel Summary", f, file_name=output_filename)

    st.markdown("### New Groupings")
    for gnum in sorted(new_assignments["Group"].unique()):
        st.markdown(f"**Group {gnum}**")
        st.dataframe(new_assignments[new_assignments["Group"] == gnum][["Student"]].reset_index(drop=True))

    # 🧮 Rebuild interaction matrix for visualizations
    st.markdown("## 📊 Interaction Visualizations")
    all_students = sorted(all_assignments["Student"].unique())
    interaction_vis_matrix = pd.DataFrame(0, index=all_students, columns=all_students)
    for course in all_assignments["Course"].unique():
        course_data = all_assignments[all_assignments["Course"] == course]
        for group in course_data["Group"].dropna().unique():
            members = course_data[course_data["Group"] == group]["Student"].tolist()
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    interaction_vis_matrix.loc[members[i], members[j]] += 1
                    interaction_vis_matrix.loc[members[j], members[i]] += 1

    # 🔥 Heatmap
    st.markdown("### Heatmap of Total Student Interactions")
    heatmap_data = interaction_vis_matrix.copy()
    heatmap_array = heatmap_data.to_numpy(dtype=float, copy=True)
    if heatmap_array.shape[0] == heatmap_array.shape[1]:
        np.fill_diagonal(heatmap_array, np.nan)
    fig3, ax3 = plt.subplots(figsize=(12, 10))
    sns.heatmap(heatmap_array, cmap="Reds", annot=True, fmt=".0f",
                linewidths=0.5, linecolor='gray', ax=ax3,
                cbar_kws={'label': 'Times Paired'},
                xticklabels=heatmap_data.columns,
                yticklabels=heatmap_data.index)
    plt.xticks(rotation=45, ha='right')
    st.pyplot(fig3)

    # 🔄 Distinct pairings
    pairwise_partners = {s: set() for s in all_students}
    for i in range(len(all_students)):
        for j in range(len(all_students)):
            if i != j and interaction_vis_matrix.iloc[i, j] > 0:
                pairwise_partners[all_students[i]].add(all_students[j])
    distinct_counts = pd.Series({s: len(p) for s, p in pairwise_partners.items()}).sort_values()

    st.markdown("### 🔄 Distinct Pairings per Student")
    fig, ax = plt.subplots(figsize=(10, 12))
    bars = ax.barh(distinct_counts.index, distinct_counts.values, color='skyblue')
    ax.set_xlabel("Number of Unique Students Paired With")
    for bar in bars:
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2, str(int(bar.get_width())), va='center')
    st.pyplot(fig)

    # 📈 Histogram of pairwise frequencies
    st.markdown("### 📈 Distribution of Student Pairing Frequency")
    pair_counts = interaction_vis_matrix.where(np.triu(np.ones(interaction_vis_matrix.shape), k=1).astype(bool)).stack()
    distribution = pair_counts.value_counts().sort_index()
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    bars = ax2.bar(distribution.index.astype(str), distribution.values, color='mediumseagreen')
    ax2.set_xlabel("Times Paired")
    ax2.set_ylabel("Number of Student Pairs")
    ax2.set_title("Histogram of Pairwise Interactions")
    for bar in bars:
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f'{int(bar.get_height())}', ha='center')
    st.pyplot(fig2)

    # 📊 Summary statistics
    st.markdown("### 📊 Summary Statistics")
    total_students = len(all_students)
    total_courses = all_assignments["Course"].nunique()
    min_val = int(distinct_counts.min())
    max_val = int(distinct_counts.max())
    mean_val = round(distinct_counts.mean(), 1)
    median_val = int(distinct_counts.median())
    std_val = round(distinct_counts.std(ddof=0), 2)
    fully_paired = sum(distinct_counts == total_students - 1)
    summary_stats = pd.DataFrame([
        {"Metric": "Total Students", "Value": total_students},
        {"Metric": "Total Courses", "Value": total_courses},
        {"Metric": "Min Distinct Interactions", "Value": min_val},
        {"Metric": "Max Distinct Interactions", "Value": max_val},
        {"Metric": "Average Distinct Interactions", "Value": mean_val},
        {"Metric": "Median Distinct Interactions", "Value": median_val},
        {"Metric": "Std Dev of Distinct Interactions", "Value": std_val},
        {"Metric": "Students Fully Paired", "Value": fully_paired}
    ])
    st.dataframe(summary_stats.set_index("Metric"))
