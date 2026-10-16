"""Theme-specific opt-in surface colors; defaults never overwrite custom viewports."""
import json,os,re,tkinter as tk
from pathlib import Path
from tkinter import ttk,colorchooser
PATH=Path(os.environ.get('APPDATA',str(Path.home()/'.config')))/'AI_Generator'/'surface_colors.json'
FIELDS=('Panels','Text boxes','Viewports','Text')
def load():
 try:return json.loads(PATH.read_text())
 except (OSError,ValueError):return {}
def palette(root):
 style=ttk.Style(root)
 return {'Panels':style.lookup('TFrame','background') or '#172033','Text boxes':style.lookup('TEntry','fieldbackground') or 'white','Viewports':style.lookup('Treeview','fieldbackground') or 'white','Text':style.lookup('TLabel','foreground') or 'black'}
def apply(root):
 from theme_manager import selected_theme
 values=load().get(selected_theme(),{});style=ttk.Style(root)
 if not values:return
 def walk(widget):
  protected=False;p=widget
  while p is not None:
   if getattr(p,'_preserve_theme_colors',False) and not getattr(p,'_custom_surface',False):protected=True;break
   p=getattr(p,'master',None)
  # Previous explicit surface overrides stay editable on the next apply.
  if getattr(widget,'_custom_surface',False):protected=False
  try:
   category='Viewports' if isinstance(widget,(tk.Canvas,ttk.Treeview)) else 'Text boxes' if isinstance(widget,(tk.Text,tk.Entry,tk.Listbox,ttk.Entry,ttk.Combobox,ttk.Spinbox)) else 'Panels' if isinstance(widget,(tk.Frame,tk.LabelFrame,ttk.Frame,ttk.LabelFrame)) else None
   if not protected and category in values:
    color=values[category]
    if isinstance(widget,ttk.Widget):
     original=getattr(widget,'_surface_base_style',None) or widget.cget('style') or widget.winfo_class();widget._surface_base_style=original
     name='CustomSurface'+str(id(widget))+'.'+original;kw={'background':color}
     if category in ('Text boxes','Viewports'):kw['fieldbackground']=color
     if 'Text' in values:kw['foreground']=values['Text']
     style.configure(name,**kw);style.map(name,fieldbackground=[('readonly',color)]);widget.configure(style=name)
    else:
     widget.configure(bg=color)
     if 'foreground' in widget.keys() and 'Text' in values:widget.configure(fg=values['Text'])
     widget._preserve_theme_colors=True
    widget._custom_surface=True
   if not protected and 'Text' in values and isinstance(widget,(tk.Label,tk.Entry,tk.Text,tk.Listbox,tk.Checkbutton,tk.Radiobutton)):
    widget.configure(fg=values['Text']);widget._preserve_theme_colors=True;widget._custom_surface=True
   elif not protected and 'Text' in values and isinstance(widget,(ttk.Label,ttk.Checkbutton,ttk.Radiobutton)):
    original=widget.cget('style') or widget.winfo_class();name='CustomText.'+original
    style.configure(name,foreground=values['Text']);widget.configure(style=name)
  except tk.TclError:pass
  for child in widget.winfo_children():walk(child)
 walk(root)
def install(root):
 if getattr(root,'_surface_settings_installed',False):return
 root._surface_settings_installed=True
 def mapped(e):
  if getattr(root,'_surface_color_pending',None):return
  def refresh():root._surface_color_pending=None;apply(root)
  root._surface_color_pending=root.after_idle(refresh)
 tag='AuthoredSurface'+str(id(root))
 def guard(e):
  w=e.widget
  if isinstance(w,tk.Canvas):w._preserve_canvas_colors=True
  elif isinstance(w,(tk.Text,tk.Entry,tk.Listbox)):
   try:
    if w.cget('background').lower() not in ('white','#ffffff','systemwindow','systembuttonface','#d9d9d9'):w._preserve_theme_colors=True
   except tk.TclError:pass
 root.bind_class(tag,'<Map>',guard,add='+')
 def register(e):
  try:
   w=e.widget
   if tag not in w.bindtags():w.bindtags((tag,)+w.bindtags())
   guard(e)
  except tk.TclError:pass
 root.bind_all('<Map>',register,add='+')
 root.bind_all('<Map>',mapped,add='+');apply(root)

def open_dialog(parent):
 from theme_manager import selected_theme
 root=parent._root();theme=selected_theme();values=load().get(theme,{});defaults=palette(root)
 win=tk.Toplevel(parent);win.title('Surface colors — '+theme);win.transient(parent.winfo_toplevel());frame=ttk.Frame(win,padding=10);frame.pack(fill='both',expand=True)
 ttk.Label(frame,text='Choose which surfaces to override. Unchecked keeps tool colors.').grid(row=0,column=0,columnspan=3,pady=(0,8))
 choices={};enabled={}
 for row,name in enumerate(FIELDS,1):
  enabled[name]=tk.BooleanVar(value=name in values);choices[name]=tk.StringVar(value=values.get(name,defaults[name]))
  ttk.Checkbutton(frame,text=name,variable=enabled[name]).grid(row=row,column=0,sticky='w')
  ttk.Entry(frame,textvariable=choices[name],width=12).grid(row=row,column=1,padx=5,pady=3)
  def pick(n=name):
   c=colorchooser.askcolor(choices[n].get(),parent=win)[1]
   if c:choices[n].set(c);enabled[n].set(True)
  ttk.Button(frame,text='Choose…',command=pick).grid(row=row,column=2)
 def save():
  data=load();result={}
  for name in FIELDS:
   if enabled[name].get():
    try:rgb=win.winfo_rgb(choices[name].get());result[name]='#'+''.join(f'{v//257:02x}' for v in rgb)
    except tk.TclError:return
  data[theme]=result;PATH.parent.mkdir(parents=True,exist_ok=True);PATH.write_text(json.dumps(data,indent=2));apply(root);win.destroy()
 ttk.Label(frame,text='Removing an override restores original colors after restart.').grid(row=5,column=0,columnspan=3,pady=8)
 ttk.Button(frame,text='Save',command=save).grid(row=6,column=2);ttk.Button(frame,text='Cancel',command=win.destroy).grid(row=6,column=1)
