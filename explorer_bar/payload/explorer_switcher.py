"""Diagonal in-window stack of open Explorer icons, with shift-wheel selection."""
import tkinter as tk
from tkinter import ttk
from PIL import Image,ImageTk
class Switcher:
 def __init__(self,explorer):
  self.explorer=explorer;self.root=explorer.frame.winfo_toplevel();self.overlay=None;self.pending=None;self.index=0;self.entries=[];self.cards=[];self.images=[];self.focus=None
  tag='ExplorerSwitcher'+str(id(self));self.tag=tag
  self.root.bind_class(tag,'<Shift-MouseWheel>',self.wheel)
  self.root.bind_class(tag,'<Tab>',self.tab)
  self.root.bind_class(tag,'<Shift-Button-4>',lambda e:self.cycle(-1))
  self.root.bind_class(tag,'<Shift-Button-5>',lambda e:self.cycle(1))
  self.root.bind_all('<Map>',lambda e:self.register(e.widget),add='+')
  def scan(w):
   self.register(w)
   for c in w.winfo_children():scan(c)
  scan(self.root)
  self.root.bind('<Control-Tab>',lambda e:self.show(),add='+')
  self.root.bind('<Tab>',self.tab,add='+')
  self.root._explorer_switcher=self
  # The compact Explorer bar already supplies the switcher icon.
  if not any(getattr(c,'_has_switcher_control',False) for c in explorer.frame.winfo_children()):
   from explorer_bar_ui import IconControl
   IconControl(explorer.frame,'stack',self.show,hint='Explorer switcher').grid(row=3,column=0,sticky='w')
 def register(self,w):
  try:
   tags=w.bindtags()
   if self.tag not in tags:w.bindtags((self.tag,)+tags)
  except tk.TclError:pass
 def tab(self,e):
  if self.overlay is not None:return self.cycle(1,False)
  if isinstance(e.widget,(tk.Entry,tk.Text,ttk.Entry,ttk.Combobox,ttk.Spinbox)):return None
  return self.show()
 def show(self):
  if self.overlay is not None:self.draw();return 'break'
  self.entries=list(self.explorer.entries.values())
  if not self.entries:return 'break'
  selected=self.explorer.selected_route()
  from tool_explorer import tool_key
  self.index=next((i for i,x in enumerate(self.entries) if tool_key(x['route'])==tool_key(selected)),0)
  self.focus=self.root.focus_get();self.images=[]
  for entry in self.entries:
   try:self.images.append(ImageTk.getimage(self.explorer.image(entry)))
   except Exception:self.images.append(None)
  self.overlay=tk.Canvas(self.root,bg='#102736',highlightthickness=1,highlightbackground='#68b6e7',takefocus=True)
  self.overlay._preserve_theme_colors=True;self.overlay.place(relx=.03,rely=.08,relwidth=.94,relheight=.82);self.overlay.lift();self.overlay.focus_set()
  self.overlay.bind('<Configure>',lambda e:self.draw());self.overlay.bind('<Button-1>',self.click)
  self.overlay.bind('<Escape>',lambda e:self.hide());self.overlay.bind('<Return>',lambda e:self.commit());self.overlay.bind('<Tab>',lambda e:self.cycle(1,False))
  self.overlay.bind('<Left>',lambda e:self.cycle(-1,False));self.overlay.bind('<Right>',lambda e:self.cycle(1,False))
  self.root.after_idle(self.draw);return 'break'
 def draw(self):
  if self.overlay is None:return
  c=self.overlay;c.delete('all');self.cards=[];self.photos=[];w=max(280,c.winfo_width());h=max(180,c.winfo_height());count=len(self.entries)
  c.create_text(15,15,anchor='nw',text='Open tools — Shift + wheel • Tab • click a card • Enter to open • Esc to cancel',fill='white',font=('Segoe UI',10))
  # Every entry is represented; many tools zoom farther out to fit the stack.
  cardw=min(240,max(32,w/(2+count*.3)));cardh=min(140,max(25,cardw*.58));dx=(w-cardw-40)/max(1,count-1);dy=(h-cardh-85)/max(1,count-1)
  order=[i for i in range(count) if i!=self.index]+[self.index]
  for i in order:
   x=20+i*dx;y=55+i*dy;selected=i==self.index
   c.create_rectangle(x+5,y+6,x+cardw+5,y+cardh+6,fill='#07121c',outline='')
   c.create_rectangle(x,y,x+cardw,y+cardh,fill='#e7f2fa' if selected else '#527288',outline='#70d3ff' if selected else '#8da8bb',width=3 if selected else 1)
   c.create_rectangle(x+1,y+1,x+cardw-1,y+21,fill='#2773ac' if selected else '#345269',outline='')
   c.create_text(x+7,y+11,anchor='w',text=self.entries[i]['label'],fill='white',font=('Segoe UI',9,'bold'),width=max(40,cardw-14))
   image=self.images[i]
   if image:
    im=image.copy();im.thumbnail((int(cardh*.5),int(cardh*.5)),Image.Resampling.LANCZOS);photo=ImageTk.PhotoImage(im,master=c);self.photos.append(photo);c.create_image(x+cardw/2,y+cardh*.58,image=photo)
   c.create_text(x+cardw/2,y+cardh-12,text=self.entries[i]['category'],fill='#163047' if selected else '#edf7ff',font=('Segoe UI',8))
   self.cards.append((x,y,x+cardw,y+cardh,i))
  c.create_text(w-12,h-12,anchor='se',text=f'{self.index+1} / {count}',fill='white')
 def cycle(self,direction,automatic=True):
  if self.overlay is None:self.show()
  if not self.entries:return 'break'
  self.index=(self.index+direction)%len(self.entries);self.draw()
  if self.pending is not None:self.root.after_cancel(self.pending);self.pending=None
  if automatic:self.pending=self.root.after(650,self.commit)
  return 'break'
 def wheel(self,e):
  if not e.delta:return 'break'
  return self.cycle(-1 if e.delta>0 else 1)
 def click(self,e):
  for x,y,xx,yy,i in reversed(self.cards):
   if x<=e.x<=xx and y<=e.y<=yy:self.index=i;self.commit();break
 def commit(self):
  if not self.entries:return
  entry=self.entries[self.index]
  from tool_explorer import tool_key
  valid=tool_key(entry['route']) in self.explorer.entries;self.hide()
  if valid:self.explorer.reopen(entry)
 def hide(self):
  if self.pending is not None:self.root.after_cancel(self.pending);self.pending=None
  if self.overlay is not None:self.overlay.destroy();self.overlay=None
  if self.focus is not None:
   try:self.focus.focus_set()
   except tk.TclError:pass
  self.photos=[]

def install(cls):
 original=cls.__init__
 def init(self,*args,**kwargs):
  original(self,*args,**kwargs);self._switcher=Switcher(self)
 cls.__init__=init
