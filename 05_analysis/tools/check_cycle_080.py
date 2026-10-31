"""Run release checks without overwriting historical implementation records."""
from pathlib import Path
import subprocess,sys,json,os
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'prompts/implementation_records/cycle_080'
jobs=[
 ('validate_prompt_079',"import validate_prompt_079 as m; m.OUT=Path('prompts/implementation_records/cycle_080/regression_079'); m.main()"),
 ('validate_prompt_077',"import validate_prompt_077 as m; m.OUT=Path('prompts/implementation_records/cycle_080/regression_077'); m.main()"),
 ('content_audit',"import audit_protocol_publication_content as m; m.OUT=Path('prompts/implementation_records/cycle_080/content_audit'); m.main()"),
]
jobs += [(Path(n).stem, f"import runpy; runpy.run_path('tools/{n}',run_name='__main__')") for n in [
 'validate_human_protocol_publication.py','validate_protocol_manuscript_propagation.py',
 'KNHANES_preverification_alignment_validator.py','validate_korean_manuscript.py',
 'validate_figure11_spacing.py','validate_main_figure_presentation.py','validate_cycle_080.py']]
results=json.loads((OUT/"commands.json").read_text()) if len(sys.argv)>1 and (OUT/"commands.json").exists() else {}
for name,code in jobs:
    if len(sys.argv)>1 and name not in sys.argv[1:]:continue
    with (OUT/(name+'.log')).open('w') as f:
        proc=subprocess.run([sys.executable,'-c',"import sys; from pathlib import Path; sys.path.insert(0,'tools'); "+code],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'MPLCONFIGDIR':'/tmp/mpl080'})
    results[name]=proc.returncode;print(name,proc.returncode,flush=True)
    (OUT/'commands.json').write_text(json.dumps(results,indent=2)+'\n')
assert all(x==0 for x in results.values()),results
