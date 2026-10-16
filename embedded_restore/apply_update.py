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
def read(name):
 rel=storage_relative(root,Path(name));return rel,(root/rel).read_text(encoding='utf-8-sig')
rel,text=read('main.py')
text=method_patch(text,'create_scrollable_tab',"from embedded_tool_ui import create_embedded_tab\nreturn create_embedded_tab(self, notebook)")
needle='self.tool_explorer = ToolExplorer(main_frame, section_notebook, self.home_launcher)'
if 'self.tool_explorer.owner = self' not in text:text=text.replace(needle,needle+'\n        self.tool_explorer.owner = self')
files[rel]=text.encode('utf8')
rel,text=read('startup_lazy.py')
body="""if self._loaded:return self._tool
if self._loading:raise RuntimeError('Recursive tool initialization: '+self._module)
self._loading=True
try:
    builder=getattr(importlib.import_module(self._module),self._name)
    self._content_parent=ttk.Frame(self._parent)
    self._content_parent.pack(fill='both',expand=True)
    try:self._tool=builder(self._content_parent,*self._args,**self._kwargs)
    except Exception:
        self._content_parent.destroy()
        raise
    self._loaded=True
    if self._binding:self._parent.unbind('<Map>',self._binding);self._binding=None
    if getattr(self,'_error_label',None):self._error_label.destroy();self._error_label=None
    return self._tool
finally:self._loading=False"""
text=method_patch(text,'_ensure',body)
marker='# Embedded launch restore'
if marker not in text:text+='\n'+marker+'\nfrom embedded_tool_ui import install_deferred as _install_deferred\n_install_deferred(DeferredTool)\n'
files[rel]=text.encode('utf8')
rel,text=read('tool_explorer.py')
if marker not in text:text+='\n'+marker+'\nfrom embedded_tool_ui import install_explorer as _install_explorer\n_install_explorer(ToolExplorer)\n'
files[rel]=text.encode('utf8')
rel=storage_relative(root,Path('photo_icon_navigation.py'))
if (root/rel).is_file():
 text=(root/rel).read_text(encoding='utf-8-sig');text=method_patch(text,'select','notebook.select(tab)');files[rel]=text.encode('utf8')
for source in payload.rglob('*'):
 if source.is_file() and '__pycache__' not in source.parts:files[storage_relative(root,source.relative_to(payload))]=source.read_bytes()
for rel,data in files.items():
 if rel.suffix=='.py':compile(data,str(rel),'exec')
backup=root/'backups'/('Embedded_Restore_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir(parents=True);records=[]
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
(backup/'changes.json').write_text(json.dumps(records,indent=2));print('Same-window tool launching and Explorer controls restored. Backup:',backup)
