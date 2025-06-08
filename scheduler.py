import pandas as pd
import numpy as np
from pyomo.environ import *
from pyomo.opt import SolverFactory, SolverManagerFactory
import os

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
    os.environ["NEOS_EMAIL"] = email

    student_names = df["Student Name"].tolist()
    student_job_types = df["Job Type"].tolist()
    unique_job_types = sorted(set(student_job_types))
    num_students = len(student_names)

    students = range(num_students)
    groups = range(len(group_sizes))

    if interaction_matrix is None:
        interaction_matrix = np.zeros((num_students, num_students), dtype=int)

    delta = (interaction_matrix == 0).astype(int)
    penalize = (interaction_matrix >= penalty_threshold).astype(int)

    if progress_callback:
        progress_callback(f"📘 Solving Course {course_num}...")
    if progress_bar:
        progress_bar.progress(1.0)

    # --------------------- Pyomo model ---------------------
    model = ConcreteModel()
    model.S = RangeSet(0, num_students - 1)
    model.G = RangeSet(0, len(group_sizes) - 1)

    model.x = Var(model.S, model.G, within=Binary)
    model.w = Var(model.S, model.S, model.G, within=Binary)

    def objective_rule(m):
        return sum(
            delta[i, j] * m.w[i, j, g] - penalty_weight * penalize[i, j] * m.w[i, j, g]
            for i in m.S for j in m.S if i < j for g in m.G
        )
    model.obj = Objective(rule=objective_rule, sense=maximize)

    model.assign_once = ConstraintList()
    for s in students:
        model.assign_once.add(sum(model.x[s, g] for g in groups) == 1)

    model.group_size = ConstraintList()
    for g in groups:
        model.group_size.add(sum(model.x[s, g] for s in students) == group_sizes[g])

    model.job_type_limit = ConstraintList()
    for g in groups:
        for job_type in unique_job_types:
            indices = [i for i, code in enumerate(student_job_types) if code == job_type]
            model.job_type_limit.add(sum(model.x[i, g] for i in indices) <= job_type_limit)

    model.lin_le = ConstraintList()
    model.lin_ge = ConstraintList()
    for i in students:
        for j in students:
            if i < j:
                for g in groups:
                    model.lin_le.add(model.w[i, j, g] <= model.x[i, g])
                    model.lin_le.add(model.w[i, j, g] <= model.x[j, g])
                    model.lin_ge.add(model.w[i, j, g] >= model.x[i, g] + model.x[j, g] - 1)

    model.cap_limit = ConstraintList()
    for i in students:
        for j in students:
            if i < j and interaction_matrix[i, j] >= max_interaction:
                for g in groups:
                    model.cap_limit.add(model.w[i, j, g] == 0)

    # --------------------- Solve ---------------------
    solver_manager = SolverManagerFactory('neos')
    solver = SolverFactory('cplex')
    solver_manager.solve(model, opt=solver, tee=False, options={"timelimit": time_limit})

    # --------------------- Extract solution ---------------------
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

    # --------------------- Append to prior if available ---------------------
    if prior_assignment_df is not None:
        full_assignment_df = pd.concat([prior_assignment_df, new_assignment_df], ignore_index=True)
    else:
        full_assignment_df = new_assignment_df.copy()

    # --------------------- Write to Excel ---------------------
    with pd.ExcelWriter(output_filename, engine='xlsxwriter') as writer:
        new_assignment_df.to_excel(writer, sheet_name="New Course", index=False)
        full_assignment_df.to_excel(writer, sheet_name="All Courses", index=False)

    if return_assignments_only:
        return new_assignment_df, full_assignment_df

    return output_filename
