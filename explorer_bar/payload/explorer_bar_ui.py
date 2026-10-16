"""Compact Explorer chrome with LED hover controls and live open-tool search."""
import tkinter as tk
from tkinter import ttk
from PIL import Image,ImageDraw,ImageTk

def matching_tools(entries,query):
 words=query.casefold().split()
 return [e for e in entries if all(word in (e.get('category','')+' '+e.get('label','')).casefold() for word in words)]

class IconControl(tk.Canvas):
 def __init__(self,parent,symbol,command,hover='#65bcff',hint='',width=28):
  bg=ttk.Style(parent).lookup('TFrame','background') or '#e5eff3'
  super().__init__(parent,width=width,height=26,bg=bg,bd=0,highlightthickness=0,takefocus=True,cursor='hand2')
  self._preserve_theme_colors=True;self.symbol=symbol;self.command=command;self.hover_color=hover;self.hint=hint;self.tip=None;self.paint(False)
  self.bind('<Enter>',lambda e:self.enter());self.bind('<Leave>',lambda e:self.leave());self.bind('<FocusIn>',lambda e:self.paint(True));self.bind('<FocusOut>',lambda e:self.paint(False))
  self.bind('<ButtonRelease-1>',lambda e:self.invoke());self.bind('<Return>',lambda e:self.invoke());self.bind('<space>',lambda e:self.invoke())
 def invoke(self):self.leave();self.command();return 'break'
 def enter(self):
  self.paint(True)
  if self.hint:
   root=self._root();self.tip=ttk.Label(root,text=self.hint,padding=3)
   x=max(0,min(root.winfo_width()-160,self.winfo_rootx()-root.winfo_rootx()));y=max(0,self.winfo_rooty()-root.winfo_rooty()-27)
   self.tip.place(x=x,y=y);self.tip.lift()
 def leave(self):
  self.paint(False)
  if self.tip is not None:self.tip.destroy();self.tip=None
 def paint(self,active):
  self.delete('all');w=int(self.cget('width'));h=26;scale=3
  im=Image.new('RGBA',(w*scale,h*scale));d=ImageDraw.Draw(im)
  color=self.hover_color if active else '#aac3d0';rgb=tuple(int(color[i:i+2],16) for i in (1,3,5))
  mask=Image.new('L',im.size);ImageDraw.Draw(mask).rounded_rectangle((3,3,w*3-4,h*3-4),radius=13,fill=255)
  for y in range(h*3):
   t=y/(h*3-1);mix=.8*(1-t/.5) if t<.5 else .12+.23*(t-.5)/.5
   d.line((0,y,w*3,y),fill=tuple(round(v*(1-mix)+255*mix) for v in rgb))
  d.rounded_rectangle((3,3,w*3-4,h*3-4),radius=13,outline='#628395',width=3);d.line((12,6,w*3-12,6),fill='white',width=2);im.putalpha(mask)
  self.photo=ImageTk.PhotoImage(im.resize((w,h),Image.Resampling.LANCZOS),master=self);self.create_image(0,0,image=self.photo,anchor='nw')
  cx=w/2;cy=13;ink='#12354a';kw={'fill':ink,'width':2}
  if self.symbol=='min':self.create_line(cx-5,cy+4,cx+5,cy+4,**kw)
  elif self.symbol=='max':self.create_rectangle(cx-5,cy-5,cx+5,cy+5,outline=ink,width=2);self.create_line(cx-5,cy-3,cx+5,cy-3,**kw)
  elif self.symbol=='close':self.create_line(cx-4,cy-4,cx+4,cy+4,**kw);self.create_line(cx+4,cy-4,cx-4,cy+4,**kw)
  elif self.symbol in ('prev','next'):
   direction=-1 if self.symbol=='prev' else 1;self.create_line(cx-direction*5,cy,cx+direction*5,cy,**kw);self.create_line(cx,cy-4,cx+direction*5,cy,cx,cy+4,**kw)
  elif self.symbol=='sort':self.create_polygon(cx-4,cy-2,cx+4,cy-2,cx,cy+3,fill=ink)
  elif self.symbol=='stack':
   for i in range(3):self.create_rectangle(cx-7+i*3,cy-6+i*3,cx+1+i*3,cy+i*3,outline=ink,width=1)

class ToolSearch:
 def __init__(self,explorer,parent):
  self.explorer=explorer;self.root=parent.winfo_toplevel();self.query=tk.StringVar();self.results=[];self.popup=None
  self.entry=tk.Entry(parent,textvariable=self.query,width=22,bg='white',fg='#17344a',insertbackground='#17344a',relief='solid',bd=1,font=('Segoe UI',10))
  self.entry._preserve_theme_colors=True;self.entry.pack(side='right',fill='x',padx=(8,3),pady=4)
  self.query.trace_add('write',lambda *_:self.update());self.entry.bind('<FocusIn>',lambda e:self.update());self.entry.bind('<Down>',self.down);self.entry.bind('<Return>',self.enter);self.entry.bind('<Escape>',lambda e:self.hide())
  self.root.bind_all('<ButtonPress-1>',self.outside,add='+')
 def outside(self,e):
  w=e.widget
  while w is not None:
   if w in (self.entry,self.popup):return
   w=getattr(w,'master',None)
  self.hide()
 def update(self):
  if not self.entry.winfo_exists() or self.root.focus_get() not in (self.entry,getattr(self,'list',None)):return
  self.results=matching_tools(list(self.explorer.entries.values()),self.query.get())
  if self.popup is None:
   self.popup=tk.Frame(self.root,bg='white',bd=1,relief='solid');self.popup._preserve_theme_colors=True
   self.list=tk.Listbox(self.popup,bg='white',fg='#17344a',selectbackground='#b7dfff',selectforeground='#17344a',font=('Segoe UI',10),bd=0,exportselection=False)
   self.list.pack(side='left',fill='both',expand=True);scroll=ttk.Scrollbar(self.popup,command=self.list.yview);scroll.pack(side='right',fill='y');self.list.configure(yscrollcommand=scroll.set)
   self.list.bind('<ButtonRelease-1>',lambda e:self.choose());self.list.bind('<Return>',lambda e:self.choose());self.list.bind('<Escape>',lambda e:self.hide())
  self.list.delete(0,'end')
  for entry in self.results:self.list.insert('end',entry['category']+' / '+entry['label'])
  if not self.results:self.list.insert('end','No matching open tools')
  self.list.configure(height=min(7,max(1,len(self.results))))
  if self.results:self.list.selection_set(0)
  width=min(330,max(220,self.root.winfo_width()-20));x=min(max(0,self.entry.winfo_rootx()-self.root.winfo_rootx()),max(0,self.root.winfo_width()-width))
  y=self.entry.winfo_rooty()-self.root.winfo_rooty()+self.entry.winfo_height()
  height=min(170,24*max(1,min(7,len(self.results)))+6)
  # Dock near the bottom: place results upward so they remain inside the window.
  if y+height>self.root.winfo_height():y=max(0,self.entry.winfo_rooty()-self.root.winfo_rooty()-height)
  self.popup.place(x=x,y=y,width=width,height=height);self.popup.lift()
 def down(self,e):
  self.update()
  if self.popup is not None:self.list.focus_set()
  return 'break'
 def enter(self,e):
  self.update();self.choose();return 'break'
 def choose(self):
  if not self.results:return
  selected=self.list.curselection();index=selected[0] if selected else 0
  entry=self.results[index];self.hide();self.explorer.reopen(entry);self.explorer.notebook.focus_set()
 def hide(self):
  if self.popup is not None:self.popup.destroy();self.popup=None

def build_bar(explorer,home,maximize,close,navigate,sort):
 bar=ttk.Frame(explorer.frame);bar.grid(row=0,column=0,columnspan=2,sticky='ew');bar._has_switcher_control=True
 for symbol,fn,color,hint in [('min',home,'#ffe426','Minimize tool to Explorer'),('max',maximize,'#48b9ff','Maximize main window'),('close',close,'#ff463f','Close current tool')]:IconControl(bar,symbol,fn,color,hint).pack(side='left',padx=1,pady=2)
 IconControl(bar,'stack',lambda:explorer.frame.winfo_toplevel()._explorer_switcher.show(),'#56d8ff','Explorer switcher').pack(side='left',padx=(4,6))
 search=ToolSearch(explorer,bar);explorer._tool_search=search
 for symbol,fn,color,hint in [('next',lambda:navigate(1),'#49baff','Next tool'),('prev',lambda:navigate(-1),'#4aee82','Previous tool')]:IconControl(bar,symbol,fn,color,hint).pack(side='right',padx=1)
 ttk.Label(bar,text='⌕').pack(side='right',padx=(6,0))
 address=ttk.Frame(bar);address.pack(side='left',fill='x',expand=True,padx=3)
 text=tk.StringVar(value='Home');label=ttk.Label(address,textvariable=text,anchor='w',padding=(6,3));label.pack(side='left',fill='x',expand=True)
 IconControl(address,'sort',sort,'#5dcaff','Sort current tool columns',width=22).pack(side='right')
 def refresh(e=None):
  route=explorer.selected_route();text.set('  ›  '.join(label for book,tab,label in route) or 'Home')
 explorer.frame.winfo_toplevel().bind_all('<<NotebookTabChanged>>',refresh,add='+');refresh()
 return bar
