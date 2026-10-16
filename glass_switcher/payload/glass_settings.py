"""Compact main settings that inherit the active theme."""
import shutil,uuid,tkinter as tk
from pathlib import Path
from tkinter import ttk,filedialog,messagebox
from PIL import Image

def active_icon_launcher(default):
 visible=[item for item in getattr(default.parent.winfo_toplevel(),'_icon_launchers',[]) if item.notebook.winfo_viewable()]
 return next((item for item in visible if item is not default and item.__class__.__name__=='GamesLauncher'),default)
def open_settings(launcher):
 launcher=active_icon_launcher(launcher);parent=launcher.parent;window=tk.Toplevel(parent);window.title('AI Generator Settings');window.transient(parent.winfo_toplevel())
 style=ttk.Style(window);window.configure(bg=style.lookup('TFrame','background') or '#172033');window.resizable(False,False)
 frame=ttk.Frame(window,padding=10);frame.pack(fill='both',expand=True);frame.columnconfigure(1,weight=1)
 from theme_manager import selected_theme,set_theme
 ttk.Label(frame,text='Settings — '+selected_theme(),font=('Segoe UI',12,'bold')).grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,8))
 config=launcher.preferences.get('background',{});path=tk.StringVar(value=config.get('image',''));mode=tk.StringVar(value=config.get('mode','Stretch'))
 ttk.Label(frame,text='Background').grid(row=1,column=0,sticky='w')
 ttk.Entry(frame,textvariable=path,width=34).grid(row=1,column=1,sticky='ew',padx=5)
 def browse():
  name=filedialog.askopenfilename(parent=window,filetypes=[('Images','*.png *.jpg *.jpeg *.webp *.bmp')])
  if name:path.set(name)
 ttk.Button(frame,text='Browse',command=browse,width=9).grid(row=1,column=2)
 ttk.Combobox(frame,textvariable=mode,values=('Stretch','Tile','Center'),state='readonly',width=12).grid(row=2,column=0,pady=5)
 def background(reset=False):
  try:
   if reset:launcher.preferences.pop('background',None);path.set('')
   else:
    source=path.get().strip()
    with Image.open(source) as image:image.verify()
    folder=launcher.root/'backgrounds';folder.mkdir(parents=True,exist_ok=True);target=folder/(uuid.uuid4().hex+Path(source).suffix.lower());shutil.copy2(source,target)
    launcher.preferences['background']={'image':str(target),'mode':mode.get()}
   launcher.save();callback=getattr(launcher,'background_changed',None)
   if callback:callback()
   launcher.schedule_layout()
  except Exception as error:messagebox.showerror('Background',str(error),parent=window)
 actions=ttk.Frame(frame);actions.grid(row=2,column=1,columnspan=2,sticky='e');ttk.Button(actions,text='Default',command=lambda:background(True)).pack(side='left',padx=3);ttk.Button(actions,text='Apply Background',command=background).pack(side='left')
 ttk.Separator(frame).grid(row=3,column=0,columnspan=3,sticky='ew',pady=6)
 icons=ttk.Frame(frame);icons.grid(row=4,column=0,columnspan=3,sticky='ew')
 for label,fn in [('Icon Settings',launcher.settings_dialog),('Show / Hide',launcher.visibility_settings),('Sort / Arrange',launcher.sort_dialog)]:ttk.Button(icons,text=label,command=fn).pack(side='left',padx=2)
 if launcher.__class__.__name__=='GamesLauncher':
  value=tk.BooleanVar(value=launcher.preferences.get('aero_console_icons',False))
  def toggle():launcher.preferences['aero_console_icons']=value.get();launcher.save();launcher.schedule_layout()
  ttk.Checkbutton(frame,text='Aero Console Icons',variable=value,command=toggle).grid(row=5,column=0,columnspan=3,sticky='w',pady=3)
 theme=tk.StringVar(value=selected_theme());ttk.Label(frame,text='Theme').grid(row=6,column=0,sticky='w',pady=5)
 ttk.Combobox(frame,textvariable=theme,values=('Neon','Modern','Dark','Retro','Aero','JuiceWRLD'),state='readonly',width=18).grid(row=6,column=1,sticky='w',padx=5)
 def save_theme():set_theme(theme.get());messagebox.showinfo('Theme','Theme saved. Restart AI Generator to apply it.',parent=window)
 ttk.Button(frame,text='Apply Theme',command=save_theme).grid(row=6,column=2)
 tools=ttk.Frame(frame);tools.grid(row=7,column=0,columnspan=3,sticky='ew',pady=5)
 from surface_settings import open_dialog
 from aero_settings import open_dialog as aero
 ttk.Button(tools,text='Surface Colors…',command=lambda:open_dialog(window)).pack(side='left',padx=2)
 ttk.Button(tools,text='Aero Glass / Blur…',command=lambda:aero(window)).pack(side='left',padx=2)
 ttk.Separator(frame).grid(row=8,column=0,columnspan=3,sticky='ew',pady=6)
 bottom=ttk.Frame(frame);bottom.grid(row=9,column=0,columnspan=3,sticky='ew')
 def maintenance():
  from app_maintenance import open_maintenance
  open_maintenance(window)
 ttk.Button(bottom,text='Update AI Generator',command=maintenance).pack(side='left')
 ttk.Button(bottom,text='Explorer Switcher',command=lambda:window._root()._explorer_switcher.show()).pack(side='left',padx=5)
 ttk.Button(bottom,text='Close',command=window.destroy).pack(side='right')
 return window

# Compatibility for visibility and maintenance dialogs using the former helper API.
from theme_manager import selected_theme as _selected
BG,TEXT,MUTED={'Aero':('#e9edef','#172b3b','#597086'),'Modern':('#ffffff','#142633','#597086'),'Dark':('#151923','#f0f3f8','#abb8ca'),'Neon':('#0b1023','#ffffff','#b7c7e6'),'Retro':('#c0c0c0','#000000','#444444'),'JuiceWRLD':('#100820','#ffffff','#c8b2df')}.get(_selected(),('#172033','#ffffff','#aabbcc'))
FIELD=BG
class GlassButton(ttk.Button):
 def __init__(self,parent,text,command,width=160,background=None):
  super().__init__(parent,text=text,command=command,width=max(5,int(width)//8));self.text=text
 def paint(self,hover=False):self.configure(text=self.text)
def round_window(window):
 try:
  from aero_settings import load
  from glass_chrome import apply_chrome
  if _selected()=='Aero':apply_chrome(window,load())
 except Exception:pass
