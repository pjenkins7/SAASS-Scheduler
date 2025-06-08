def run_scheduler_single_course(
    df,
    course_num,
    email,
    group_sizes,
    interaction_matrix=None,
    job_type_limit=2,
    penalty_threshold=3,
    max_interaction=4,
    penalty_weight=0.25,
    time_limit=20,
    progress_callback=None,
    progress_bar=None,
    output_filename="SAASS_Scheduler_Output.xlsx",
    prior_assignment_df=None,
    return_assignments_only=False
):
    ...
    # [same setup and model as your original — unchanged]

    # --------------------- Extract and Format Output ---------------------
    assignment_rows = []
    courseGroups = {g: [] for g in groups}
    for s in students:
        for g in groups:
            if value(model.x[s, g]) > 0.5:
                courseGroups[g].append(s)

    for g in groups:
        for s in courseGroups[g]:
            assignment_rows.append({
                "Course": course_num,
                "Group": g + 1,
                "Student": student_names[s],
                "Job Type": student_job_types[s]
            })

    new_assignment_df = pd.DataFrame(assignment_rows)

    # 🧩 Append to prior assignments if provided
    if prior_assignment_df is not None:
        full_assignment_df = pd.concat([prior_assignment_df, new_assignment_df], ignore_index=True)
    else:
        full_assignment_df = new_assignment_df.copy()

    # 📝 Save Excel with both tabs
    with pd.ExcelWriter(output_filename, engine='xlsxwriter') as writer:
        new_assignment_df.to_excel(writer, sheet_name="New Course", index=False)
        full_assignment_df.to_excel(writer, sheet_name="All Courses", index=False)

    if return_assignments_only:
        return new_assignment_df, full_assignment_df
    return output_filename
