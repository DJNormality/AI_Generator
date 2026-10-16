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

# Retain theme normalization and expose a live blur-strength percentage.
rel,text=read('aero_settings.py')
if '# Blur strength setting' not in text:
 text=text.replace('def normalize(data):',"# Blur strength setting\nDEFAULT['blur_strength']=55\ndef normalize(data):")
 text=text.replace("    return {'color':color.lower()", "    try:strength=max(0,min(100,float(data.get('blur_strength',55))))\n    except (ValueError,TypeError):strength=55\n    return {'blur_strength':strength,'color':color.lower()")
 text=text.replace("trans=tk.DoubleVar(value=original['transparency'])", "trans=tk.DoubleVar(value=original['transparency']);strength=tk.DoubleVar(value=original.get('blur_strength',55))")
 text=text.replace("{'color':color,'transparency':trans.get()", "{'blur_strength':strength.get(),'color':color,'transparency':trans.get()")
 text=text.replace("[('Transparency',trans,85),", "[('Blur %',strength,100),('Transparency',trans,85),")
 scale_line="        ttk.Scale(mixer,from_=0,to=maximum,variable=var,command=changed,length=270).grid(row=row,column=1,padx=12)"
 readout=scale_line+"\n        unit='°' if label=='Hue' else '%'\n        value_label=tk.StringVar(value=f'{var.get():.0f}'+unit)\n        if not hasattr(window,'_slider_labels'):window._slider_labels=[]\n        window._slider_labels.append(value_label)\n        var.trace_add('write',lambda *_,v=var,s=value_label,u=unit:s.set(f'{v.get():.0f}'+u))\n        ttk.Label(mixer,textvariable=value_label,width=5).grid(row=row,column=2)"
 text=text.replace(scale_line,readout)
 text=text.replace("padding=16", "padding=10").replace("length=270", "length=220").replace("font=('Segoe UI',-18)", "font=('Segoe UI',-15)")
files[rel]=text.encode('utf8')
rel,text=read('theme_manager.py')
if 'from surface_settings import install' not in text:
 text=text.replace(' apply(root)', ' apply(root)\n from surface_settings import install\n install(root)',1)
files[rel]=text.encode('utf8')
rel,text=read('tool_explorer.py')
# Include the embedded Explorer wrapper once, then extend it with the switcher.
text=files[rel].decode('utf8')
if '# Explorer diagonal switcher' not in text:text+='\n# Explorer diagonal switcher\nfrom explorer_switcher import install as _install_switcher\n_install_switcher(ToolExplorer)\n'
files[rel]=text.encode('utf8')
# Protect explicit custom surfaces from global palette repaint handlers.
for name in ('neon_theme.py','aero_theme.py','modern_theme.py'):
 rel,text=read(name)
 tree=ast.parse(text);lines=text.splitlines(keepends=True)
 guards=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.FunctionDef) and node.name=='mapped':
   segment=''.join(lines[node.lineno-1:node.end_lineno])
   if '_preserve_theme_colors' in segment and (name!='neon_theme.py' or '_preserve_canvas_colors' in segment):continue
   assignment=next((n for n in node.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='widget' for t in n.targets)),None)
   if assignment:
    line=lines[assignment.lineno-1];indent=line[:len(line)-len(line.lstrip())]
    guard=indent+"if isinstance(widget,(tk.Text,tk.Entry,tk.Listbox)) and widget.cget('background').lower() in ('black','#000000') :return\n"+(indent+"if isinstance(widget,tk.Canvas):\n"+indent+"    widget._preserve_canvas_colors=True;return\n" if name=='neon_theme.py' else '')+indent+"ancestor=widget\n"+indent+"while ancestor is not None:\n"+indent+"    if getattr(ancestor,'_preserve_theme_colors',False):return\n"+indent+"    ancestor=getattr(ancestor,'master',None)\n"
    guards.append((assignment.end_lineno,guard))
 for line,guard in sorted(guards,reverse=True):lines[line:line]=[guard]
 text=''.join(lines)
 if name=='aero_theme.py' and '# Preserve authored panel backgrounds' not in text:
  tree=ast.parse(text);panel=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='style_panel')
  lines=text.splitlines(keepends=True);line=panel.body[0].end_lineno if isinstance(panel.body[0],ast.Expr) else panel.lineno
  guard="    # Preserve authored panel backgrounds\n    if isinstance(widget,(tk.Frame,tk.LabelFrame,tk.PanedWindow)):\n        try:\n            current=widget.cget('background').lower()\n            allowed={BG.lower(),PANEL.lower(),getattr(widget,'_aero_panel_last_color','').lower(),'#d9d9d9','#f0f0f0','systembuttonface','white','#ffffff'}\n            if current not in allowed:return\n            widget._aero_panel_last_color=BG\n        except tk.TclError:pass\n"
  lines[line:line]=[guard];text=''.join(lines)
 files[rel]=text.encode('utf8')
rel,text=read('home_launcher.py')
text=method_patch(text,'home_settings','from glass_settings import open_settings\nreturn open_settings(self)');files[rel]=text.encode('utf8')
for source in payload.rglob('*'):
 if source.is_file() and '__pycache__' not in source.parts:files[storage_relative(root,source.relative_to(payload))]=source.read_bytes()
for rel,data in files.items():
 if rel.suffix=='.py':compile(data,str(rel),'exec')
backup=root/'backups'/('Glass_Switcher_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir(parents=True);records=[]
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
(backup/'changes.json').write_text(json.dumps(records,indent=2));print('Theme surfaces, compact settings, blur strength and diagonal Explorer switcher installed. Backup:',backup)
