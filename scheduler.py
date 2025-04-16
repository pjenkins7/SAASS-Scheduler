# scheduler.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pyomo.environ import *
from pyomo.opt import SolverFactory, SolverManagerFactory
import os

def run_scheduler(df, email, progress_callback=None):
    os.environ["NEOS_EMAIL"] = email

    student_afscs = df["AFSC"].tolist()
    student_names = df["Student Name"].tolist()
    unique_afscs = sorted(set(student_afscs))

    num_students = len(student_names)
    students = range(num_students)
    groups = range(4)
    
    base_size = num_students // 4
    extra = num_students % 4
    group_sizes = [base_size + 1 if i < extra else base_size for i in range(4)]

    interaction_matrix = np.zeros((num_students, num_students), dtype=int)
    max_interaction = 4
    penalty_threshold = 3
    penalty_weight = 0.25
    time_limit = 20

    course_numbers = [601, 600, 627, 632, 628, 633, 644, 667, 665, 660]
    summary_rows = []
    assignment_rows = []

    for course_num in course_numbers:
        if progress_callback:
            progress_callback(f"📘 Solving Course {course_num}...")

        delta = (interaction_matrix == 0).astype(int)
        penalize = (interaction_matrix >= penalty_threshold).astype(int)

        model = ConcreteModel()
        model.S = RangeSet(0, num_students - 1)
        model.G = RangeSet(0, 3)

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

        model.afsc_limit = ConstraintList()
        for g in groups:
            for afsc in unique_afscs:
                indices = [i for i, code in enumerate(student_afscs) if code == afsc]
                model.afsc_limit.add(sum(model.x[i, g] for i in indices) <= 2)

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

        solver_manager = SolverManagerFactory('neos')
        solver = SolverFactory('cplex')
        solver.options['timelimit'] = time_limit
        solver_manager.solve(model, opt=solver, tee=False)

        courseGroups = {g: [] for g in groups}
        for s in students:
            for g in groups:
                if value(model.x[s, g]) > 0.5:
                    courseGroups[g].append(s)

        for g in groups:
            group = courseGroups[g]
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    interaction_matrix[a, b] += 1
                    interaction_matrix[b, a] += 1

        for g in groups:
            for s in courseGroups[g]:
                assignment_rows.append({
                    "Course": course_num,
                    "Group": g + 1,
                    "Student Name": student_names[s],
                    "AFSC": student_afscs[s]
                })

        # Summary statistics for this course (final ones are shown only once)
        pairwiseCounts = interaction_matrix[np.triu_indices(num_students, k=1)]
        studentTotals = np.sum(interaction_matrix > 0, axis=1)

    # Save combined Excel sheet
    summary_df = pd.DataFrame(assignment_rows)

    summary_stats = {
        "Unmet Pairs": np.sum(pairwiseCounts == 0),
        "Max Pairwise": np.max(pairwiseCounts),
        "Pairs at Cap": np.sum(pairwiseCounts >= max_interaction),
        "Min Student": np.min(studentTotals),
        "Max Student": np.max(studentTotals),
        "Avg Student": round(np.mean(studentTotals), 2),
        "Median": np.median(studentTotals),
        "Fully Paired": np.sum(studentTotals == (num_students - 1))
    }

    with pd.ExcelWriter("AY26_Scheduler_Summary.xlsx", engine='xlsxwriter') as writer:
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

        # Space row
        spacer = pd.DataFrame([["", "", "", ""]], columns=summary_df.columns)
        pd.concat([summary_df, spacer], ignore_index=True).to_excel(writer, sheet_name='Summary', index=False)

        # Stats appended
        pd.DataFrame([summary_stats]).to_excel(writer, sheet_name='Summary', startrow=len(summary_df) + 2, index=False)

        # Final interaction matrix
        pd.DataFrame(interaction_matrix, columns=student_names, index=student_names).to_excel(
            writer, sheet_name="Interaction Matrix"
        )

    # Final visuals
    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(interaction_matrix, cmap='Reds', vmin=0, vmax=max_interaction)
    for i in range(num_students):
        for j in range(num_students):
            label = "X" if i == j else str(interaction_matrix[i, j])
            ax.text(j, i, label, ha='center', va='center', color='black')
    ax.set_xticks(np.arange(num_students))
    ax.set_yticks(np.arange(num_students))
    ax.set_xticklabels(student_names, rotation=90)
    ax.set_yticklabels(student_names)
    plt.colorbar(im, ax=ax, ticks=range(max_interaction + 1))
    plt.title("Final Interaction Matrix")
    plt.tight_layout()
    plt.savefig("Heatmap_Final.png")
    plt.close()

    # Final bar chart
    fig, ax = plt.subplots(figsize=(10, 10))
    sorted_counts = np.sort(studentTotals)
    sorted_names = [student_names[i] for i in np.argsort(studentTotals)]
    bars = ax.barh(range(num_students), sorted_counts, color=(0.4, 0.6, 0.8))
    for i, bar in enumerate(bars):
        ax.text(bar.get_width() - 1, bar.get_y() + bar.get_height()/2, str(sorted_counts[i]),
                va='center', ha='right', color='white', fontweight='bold')
    ax.set_yticks(range(num_students))
    ax.set_yticklabels(sorted_names)
    ax.set_xlabel("Number of Unique Interactions")
    ax.set_ylabel("Student")
    ax.set_title("Total Distinct Pairings per Student")
    plt.tight_layout()
    plt.savefig("InteractionBar_Final.png")
    plt.close()

    return "AY26_Scheduler_Summary.xlsx", course_numbers
