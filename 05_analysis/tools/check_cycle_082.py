"""Run historical and current checks, isolating every report in cycle082."""
from pathlib import Path
import subprocess,sys,json,os
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'prompts/implementation_records/cycle_082'
jobs=[
 ('validate_prompt_079',"import validate_prompt_079 as m; m.OUT=Path('prompts/implementation_records/cycle_082/regression_079'); m.main()"),
 ('validate_prompt_077',"import validate_prompt_077 as m; m.OUT=Path('prompts/implementation_records/cycle_082/regression_077'); m.main()"),
 ('content_audit',"import audit_protocol_publication_content as m; m.OUT=Path('prompts/implementation_records/cycle_082/content_audit'); m.main()"),
]
for name in ['validate_human_protocol_publication','validate_protocol_manuscript_propagation','KNHANES_preverification_alignment_validator','validate_korean_manuscript','validate_figure11_spacing','validate_main_figure_presentation','validate_cycle_081','test_cycle_081','validate_cycle_082','test_cycle_082']:
    # Isolate standalone scripts even when their output assignment is top-level.
    code=f"p=Path('tools/{name}.py'); s=p.read_text(); "
    code+="import re; s=re.sub(r'(?m)^(OUT|OUTPUT)\\s*=.*$', lambda m:m[1]+\"=Path('prompts/implementation_records/cycle_082/\"+('verification' if m[1]=='OUT' else 'output')+\"_"+name+".json').resolve()\", s)" if name not in ['validate_cycle_081','test_cycle_081','validate_cycle_082','test_cycle_082'] else "s=s"
    code+="; s=s.replace('cycle_081','cycle_082'); s=s.replace('prompts/implementation_records/figure11_spacing_20260924.json','prompts/implementation_records/cycle_082/figure11_spacing.json'); exec(compile(s,str(p),'exec'),{'__name__':'__main__','__file__':str(p.resolve())})"
    jobs.append((name,code))
results=json.loads((OUT/'commands.json').resolve().read_text()) if len(sys.argv)>1 and (OUT/'commands.json').resolve().exists() else {}
for name,code in jobs:
    if len(sys.argv)>1 and name not in sys.argv[1:]:continue
    run=1
    while (OUT/f'{name}_run{run}.log').exists():run+=1
    with (OUT/f'{name}_run{run}.log').open('w') as f:
        proc=subprocess.run([sys.executable,'-c',"import sys; from pathlib import Path; sys.path.insert(0,'tools'); "+code],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'MPLCONFIGDIR':'/tmp/mpl082'})
    results[name]={'exit_code':proc.returncode,'log':f.name};print(name,proc.returncode,flush=True)
    (OUT/'commands.json').resolve().write_text(json.dumps(results,indent=2)+'\n')
assert all(x['exit_code']==0 for x in results.values()),results
