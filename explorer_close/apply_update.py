"""Repair overlapping rows, tool panels, scrolling, and Explorer Close All."""
from pathlib import Path
import ast,datetime,shutil,json,sys
root=Path(__file__).resolve().parents[3];payload=Path(__file__).resolve().parent/'payload'
if not (root/'main.py').is_file():raise SystemExit('Copy this package into the existing AI Generator installation.')
if (root/'directory_runtime.py').is_file():
 sys.path.insert(0,str(root));from directory_runtime import storage_relative
else:
 def storage_relative(root,rel):return rel

def method_patch(text,name,body):
 tree=ast.parse(text);method=next((node for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and node.name==name),None)
 if method is None:raise ValueError('Required method missing: '+name)
 lines=text.splitlines(keepends=True);indent=lines[method.lineno-1][:len(lines[method.lineno-1])-len(lines[method.lineno-1].lstrip())];replacement=indent+'def '+name+'('+', '.join(arg.arg for arg in method.args.args)+'):\n'
 replacement+=''.join(indent+'    '+line+'\n' for line in body.splitlines());lines[method.lineno-1:method.end_lineno]=[replacement];return ''.join(lines)

files={}
rel=storage_relative(root,Path('tool_explorer.py'));text=(root/rel).read_text(encoding='utf-8-sig')
if '# Explorer icon close repair' not in text:text+='\n# Explorer icon close repair\nfrom explorer_close_fix import install as _install_close_fix\n_install_close_fix(ToolExplorer)\n'
files[rel]=text.encode('utf8')
for source in payload.rglob('*'):
 if source.is_file() and '__pycache__' not in source.parts:files[storage_relative(root,source.relative_to(payload))]=source.read_bytes()
for rel,data in files.items():
 if rel.suffix=='.py':compile(data,str(rel),'exec')
backup=root/'backups'/('Explorer_Close_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir(parents=True);records=[]
try:
 for rel,data in files.items():
  target=root/rel;existed=target.exists()
  if existed:
   saved=backup/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
  records.append({'path':str(rel),'existed':existed});target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
except Exception:
 for record in reversed(records):
  target=root/record['path']
  if record['existed']:shutil.copy2(backup/record['path'],target)
  elif target.exists():target.unlink()
 raise
(backup/'changes.json').write_text(json.dumps(records,indent=2));print('Explorer Close and Close All icon removal repaired. Backup:',backup)
