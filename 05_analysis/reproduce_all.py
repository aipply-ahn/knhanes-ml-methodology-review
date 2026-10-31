"""Order of the steps that regenerate the review outputs inside the project layout (see README.md)."""
import subprocess, sys
STEPS = ["tools/checklist_v22.py", "tools/build_data1_workbook.py", "tools/make_main_figures.py", "tools/build_standalone_supplements.py"]
if __name__ == "__main__":
    for s in STEPS:
        print("running", s, flush=True)
        subprocess.run([sys.executable, s], check=True)
