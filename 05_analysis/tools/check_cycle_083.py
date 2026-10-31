"""Historical and current regressions with output-only redirection to cycle083."""
from pathlib import Path
import subprocess,sys,json,os
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'prompts/implementation_records/cycle_083'
jobs=[]
for name in ['validate_prompt_079','validate_prompt_077','audit_protocol_publication_content']:
 jobs.append((name,f"import {name} as m; m.OUT=Path('prompts/implementation_records/cycle_083/{name}'); m.main()"))
for name in ['validate_human_protocol_publication','validate_protocol_manuscript_propagation','KNHANES_preverification_alignment_validator','validate_korean_manuscript','validate_figure11_spacing','validate_main_figure_presentation','validate_cycle_081','test_cycle_081','validate_cycle_082','test_cycle_082','test_cycle_083']:
 code=f"p=Path('tools/{name}.py'); s=p.read_text(); import re; "
 if name=='test_cycle_082':
  code+="s=s.replace(\"(OUT/'applicability_tests.json')\",\"(Path('prompts/implementation_records/cycle_083')/'applicability_tests.json')\"); "
 elif name in ['validate_cycle_081','test_cycle_081','validate_cycle_082']:
  cycle='081' if '081' in name else '082'
  code+=f"s=s.replace(\"OUT=ROOT/'prompts/implementation_records/cycle_{cycle}'\",\"OUT=ROOT/'prompts/implementation_records/cycle_083'\"); "
 elif name!='test_cycle_083':
  code+="s=re.sub(r'(?m)^(OUT|OUTPUT)\\s*=.*$',lambda m:m[1]+\"=Path('prompts/implementation_records/cycle_083/\"+'"+name+"'+\".json').resolve()\",s); "
 code+="s=s.replace('prompts/implementation_records/figure11_spacing_20260924.json','prompts/implementation_records/cycle_083/figure11_spacing.json'); exec(compile(s,str(p),'exec'),{'__name__':'__main__','__file__':str(p.resolve())})"
 jobs.append((name,code))
results=json.loads((OUT/'commands.json').read_text()) if (OUT/'commands.json').exists() else {}
for name,code in jobs:
 if len(sys.argv)>1 and name not in sys.argv[1:]:continue
 run=1
 while (OUT/f'{name}_run{run}.log').exists():run+=1
 with (OUT/f'{name}_run{run}.log').open('w') as log:
  proc=subprocess.run([sys.executable,'-c',"import sys; from pathlib import Path; sys.path.insert(0,'tools'); "+code],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'MPLCONFIGDIR':'/tmp/mpl083'})
 results[name]={'exit_code':proc.returncode,'log':str(Path(log.name).relative_to(ROOT))};print(name,proc.returncode,flush=True)
 (OUT/'commands.json').write_text(json.dumps(results,indent=2)+'\n')
assert all(r['exit_code']==0 for r in results.values())
