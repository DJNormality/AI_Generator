"""Glass chrome with opaque editing surfaces and glossy blue controls."""
import tkinter as tk
from tkinter import ttk
from PIL import Image,ImageDraw,ImageTk

def glossy(color,size=(54,44)):
 w,h=size;im=Image.new('RGBA',(w*3,h*3));d=ImageDraw.Draw(im);rgb=tuple(int(color[i:i+2],16) for i in (1,3,5))
 mask=Image.new('L',im.size);ImageDraw.Draw(mask).rounded_rectangle((2,2,w*3-3,h*3-3),radius=15,fill=255)
 for y in range(h*3):
  t=y/(h*3);mix=.75*(1-t/.48) if t<.48 else .1+.25*(t-.48)/.52
  c=tuple(round(v*(1-mix)+255*mix) for v in rgb);d.line((0,y,w*3,y),fill=c)
 d.rounded_rectangle((2,2,w*3-3,h*3-3),radius=15,outline='#6694b3',width=3)
 d.rounded_rectangle((5,5,w*3-6,h*3-6),radius=12,outline='#e7f5ff',width=2);im.putalpha(mask)
 return im.resize(size,Image.Resampling.LANCZOS)

def install(theme):
 import neon_theme as neon
 original_apply=theme.apply;original_update=theme.update_preferences
 theme.button_image=lambda w,h,active=False:glossy('#70bcef' if active else '#9ed4fa',(max(4,int(w)),max(4,int(h))))
 def skin(widget,style):
  widget._neon_skinned=True
  if getattr(widget,'_aero_blue_skinned',False):return
  widget._aero_blue_skinned=True;widget.configure(style='AeroBlue.TButton')
 def surface(root):
  state=root._aero_controller['settings'];style=ttk.Style(root)
  # Opaque widgets retain their authored or user-selected backgrounds.
  def walk(widget):
   try:
    if isinstance(widget,ttk.Button) and not getattr(widget,'_preserve_theme_colors',False):skin(widget,style)
   except tk.TclError:pass
   for child in widget.winfo_children():walk(child)
  walk(root)
  for window,blur in list(root._aero_controller['windows'].items()):
   blur.enabled=False;blur.hide()
   try:
    window.attributes('-alpha',1.0)
    if root.tk.call('tk','windowingsystem')=='win32':window.attributes('-transparentcolor','')
    try:
     from glass_chrome import apply_chrome
     apply_chrome(window,state)
    except Exception:pass
   except tk.TclError:pass
 def apply(root):
  neon.skin_button=skin;original_apply(root)
  style=ttk.Style(root);photos=[ImageTk.PhotoImage(glossy(c,(60,30)),master=root) for c in ('#9ed4fa','#70bcef','#58a9e0','#ceddeb')]
  root._aero_blue_photos=photos
  if 'AeroBlue.face' not in style.element_names():style.element_create('AeroBlue.face','image',photos[0],('disabled',photos[3]),('pressed',photos[2]),('active',photos[1]),border=7,sticky='nswe')
  style.layout('AeroBlue.TButton',[('AeroBlue.face',{'sticky':'nswe','children':[('Button.padding',{'sticky':'nswe','children':[('Button.label',{'sticky':'nswe'})]})]})])
  style.configure('AeroBlue.TButton',padding=(10,5),foreground='#173e5b',font=('Segoe UI',-14))
  style.map('AeroBlue.TButton',foreground=[('disabled','#718594'),('active','#173e5b')])
  def mapped(e):
   if getattr(root,'_aero_surface_pending',None):return
   def refresh():
    root._aero_surface_pending=None
    if root.winfo_exists():surface(root)
   root._aero_surface_pending=root.after_idle(refresh)
  root.bind_all('<Map>',mapped,add='+');surface(root)
 def update(root,settings):
  original_update(root,settings);surface(root)
 theme.apply=apply;theme.update_preferences=update
