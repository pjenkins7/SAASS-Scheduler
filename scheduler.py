# scheduler.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pyomo.environ import *
from pyomo.opt import SolverFactory, SolverManagerFactory
import os

def run_scheduler(df, email):
    os.environ["NEOS_EMAIL"] = email

    student_afscs = df["AFSC"].tolist()
    student_names = df["Student Name"].tolist()
    unique_afscs = sorted(set(student_afscs))

    num_students = len(student_names)
    students = range(num_students)
    groups = range(4)
    
    # Evenly divide students across 4 groups
    base_size = num_students // 4
    extra = num_students % 4  # Distribute the remainder

    # Build group sizes like [base+1, base+1, base, base] if extra = 2
    group_sizes = [base_size + 1 if i < extra else base_size for i in range(4)]

    interaction_matrix = np.zeros((num_students, num_students), dtype=int)
    max_interaction = 4
    penalty_threshold = 3
    penalty_weight = 0.25
    time_limit = 20

    course_numbers = [601, 600, 627, 632, 628, 633, 644, 667, 665, 660]

    writer = pd.ExcelWriter("AY26_Scheduler_Summary.xlsx", engine='xlsxwriter')
    summary_rows = []

    course_tab_names = {
        601: '601 - Strategy',
        600: '600 - Theory',
        627: '627 - Total War',
        632: '632 - Intl Politics',
        628: '628 - Limited War',
        633: '633 - Coercion',
        644: '644 - IW',
        667: '667 - Cyber',
        665: '665 - Space',
        660: '660 - Innovation'
    }

    for course_num in course_numbers:
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

        pd.DataFrame(interaction_matrix, columns=student_names, index=student_names).to_excel(
            writer, sheet_name=f"Matrix {course_num}")

        sheet_name = course_tab_names.get(course_num, str(course_num))
        group_data = []
        for g in groups:
            for s in courseGroups[g]:
                group_data.append({
                    "Course": course_num,
                    "Group": g + 1,
                    "Student Index": s,
                    "Student Name": student_names[s],
                    "AFSC": student_afscs[s]
                })
        group_df = pd.DataFrame(group_data)
        group_df.to_excel(writer, sheet_name=sheet_name, index=False)

        # Summary statistics
        pairwiseCounts = interaction_matrix[np.triu_indices(num_students, k=1)]
        unmetPairs = np.sum(pairwiseCounts == 0)
        maxPairwise = np.max(pairwiseCounts)
        pairsAtCap = np.sum(pairwiseCounts >= max_interaction)

        studentTotals = np.sum(interaction_matrix > 0, axis=1)
        minStudent = np.min(studentTotals)
        maxStudent = np.max(studentTotals)
        avgStudent = np.mean(studentTotals)
        medianStudent = np.median(studentTotals)
        fullyPaired = np.sum(studentTotals == (num_students - 1))

        summary_rows.append({
            "Course": course_num,
            "Unmet Pairs": unmetPairs,
            "Max Pairwise": maxPairwise,
            "Pairs at Cap": pairsAtCap,
            "Min Student": minStudent,
            "Max Student": maxStudent,
            "Avg Student": round(avgStudent, 2),
            "Median": medianStudent,
            "Fully Paired": fullyPaired
        })

        # Save plots
        plt.figure(figsize=(12, 10))
        plt.imshow(interaction_matrix, cmap='Reds', vmin=0, vmax=max_interaction)
        plt.colorbar(ticks=range(max_interaction + 1))
        plt.title(f"Interaction Matrix After Course {course_num}")
        plt.xticks(range(num_students), student_names, rotation=90)
        plt.yticks(range(num_students), student_names)
        plt.tight_layout()
        plt.savefig(f"Heatmap_Course{course_num}.png")
        plt.close()

        plt.figure(figsize=(10, 10))
        sorted_counts = np.sort(studentTotals)
        sorted_names = [student_names[i] for i in np.argsort(studentTotals)]
        bars = plt.barh(range(num_students), sorted_counts, color=(0.4, 0.6, 0.8))
        for i, bar in enumerate(bars):
            plt.text(bar.get_width() - 1, bar.get_y() + bar.get_height()/2, str(sorted_counts[i]),
                     va='center', ha='right', color='white', fontweight='bold')
        plt.yticks(range(num_students), sorted_names)
        plt.xlabel("Number of Unique Interactions")
        plt.title(f"Distinct Interactions After Course {course_num}")
        plt.tight_layout()
        plt.savefig(f"InteractionBar_Course{course_num}.png")
        plt.close()

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_excel(writer, sheet_name='Summary', index=False)
    writer.close()

    return "AY26_Scheduler_Summary.xlsx"
