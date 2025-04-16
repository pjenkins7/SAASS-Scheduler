# SAASS-Scheduler

This web-based tool allows users to upload SAASS student data, submit group scheduling problems to the NEOS server using Pyomo, and download results with interaction matrices and visualizations.

## How It Works
- Upload a CSV of student names, AFSCs / job descriptions
- Enter your email (required for NEOS submission).
- The app sends an optimization job to NEOS using the CPLEX solver.
- You get downloadable results and visualizations.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
