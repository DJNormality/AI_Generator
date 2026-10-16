"""Dedicated tool windows, click-armed scrolling, and stable table sorting."""
import datetime,math,re,tkinter as tk
from pathlib import Path
from tkinter import ttk
SORT_FIELDS=('Name','Size','Date','Type','Location')

def sort_value(value,field):
 text=str(value or '').strip()
 if field=='Size':
  match=re.search(r'([-+]?\d[\d,]*(?:\.\d+)?)\s*(bytes?|[kmgt]i?b)?',text,re.I)
  if match:
   unit=(match.group(2) or '').lower();power={'kb':1,'kib':1,'mb':2,'mib':2,'gb':3,'gib':3,'tb':4,'tib':4}.get(unit,0)
   return (0,float(match.group(1).replace(',',''))*(1024**power))
 if field=='Date':
  for fmt in ('%Y-%m-%d %H:%M:%S','%Y-%m-%d','%m/%d/%Y','%m/%d/%Y %H:%M'):
   try:return (0,datetime.datetime.strptime(text,fmt).timestamp())
   except ValueError:pass
 return (1,text.casefold())

class ScrollRouter:
 def __init__(self,root):
  self.root=root;self.armed=None;self.tag='ToolWindowScroll'+str(id(self));self.widgets=set()
  root.bind_class(self.tag,'<ButtonPress-1>',self.click,add='+')
  for sequence in ('<MouseWheel>','<Button-4>','<Button-5>'):root.bind_class(self.tag,sequence,self.wheel)
  root.bind_all('<Map>',self.mapped,add='+');self.scan(root)
 def scan(self,widget):
  self.register(widget)
  for child in widget.winfo_children():self.scan(child)
 def mapped(self,event):self.register(event.widget)
 def register(self,widget):
  if widget in self.widgets:return
  try:
   if self.tag not in widget.bindtags():widget.bindtags((self.tag,)+widget.bindtags())
   self.widgets.add(widget)
   widget.bind('<Destroy>',lambda e:self.widgets.discard(e.widget),add='+')
   if isinstance(widget,ttk.Treeview):enhance_tree(widget)
  except tk.TclError:pass
 def region(self,widget):
  while widget is not None:
   if isinstance(widget,(ttk.Treeview,tk.Listbox,tk.Text)):return widget
   if getattr(widget,'_scroll_canvas',None) is not None:return widget._scroll_canvas
   if isinstance(widget,tk.Canvas):
    try:
     if widget.cget('yscrollcommand') and not getattr(widget,'_editing_viewport',False):return widget
    except tk.TclError:pass
   widget=getattr(widget,'master',None)
  return None
 def click(self,event):
  region=self.region(event.widget)
  if region is not None:self.armed=region
 def wheel(self,event):
  try:
   target=self.region(event.widget)
   # Native entries/comboboxes retain their own wheel behavior.
   if isinstance(event.widget,(ttk.Combobox,ttk.Spinbox,tk.Spinbox)):return None
   if isinstance(event.widget,tk.Canvas) and event.widget.bind('<MouseWheel>'):return None
   if target is None:return None
   if target is not self.armed or not target.winfo_exists():return 'break'
   number=getattr(event,'num',None);delta=getattr(event,'delta',0)
   steps=-3 if number==4 or delta>0 else 3
   if number not in (4,5) and not delta:return None
   if event.state&1 and hasattr(target,'xview_scroll'):target.xview_scroll(steps,'units')
   else:target.yview_scroll(steps,'units')
   return 'break'
  except tk.TclError:return None

def install_router(root):
 if not hasattr(root,'_tool_scroll_router'):root._tool_scroll_router=ScrollRouter(root)
 return root._tool_scroll_router

class TableSorter:
 def __init__(self,tree):self.tree=tree;self.direction={}
 def columns(self):
  cols=self.tree.cget('columns');cols=self.tree.tk.splitlist(cols) if isinstance(cols,str) else cols
  return ['#0']+list(cols)
 def field_column(self,field):
  aliases={'Name':('name','file','filename','asset','model','title'),'Size':('size','bytes','length'),'Date':('date','modified','created','mtime'),'Type':('type','extension','format','kind'),'Location':('location','path','directory','source','archive')}
  for col in self.columns():
   title=self.tree.heading(col,'text').replace(' ▾','').casefold();key=str(col).casefold()
   if any(a==key or a in title for a in aliases[field]):return col
  return '#0' if field=='Name' and 'tree' in str(self.tree.cget('show')) else None
 def sort(self,column,field=None):
  if column is None:return
  field=field or next((f for f in SORT_FIELDS if self.field_column(f)==column),'Name');descending=self.direction.get(column,False)
  def reorder(parent=''):
   children=list(self.tree.get_children(parent));key=lambda iid:sort_value(self.tree.item(iid,'text') if column=='#0' else self.tree.set(iid,column),field)
   for index,iid in enumerate(sorted(children,key=key,reverse=descending)):self.tree.move(iid,parent,index);reorder(iid)
  selected=self.tree.selection();reorder();self.tree.selection_set(selected);self.direction[column]=not descending
 def menu(self,event):
  menu=tk.Menu(self.tree,tearoff=False,bg='#173e69',fg='white',activebackground='#2a6da8',activeforeground='white')
  for field in SORT_FIELDS:
   column=self.field_column(field);menu.add_command(label='Sort by '+field,command=lambda c=column,f=field:self.sort(c,f),state='normal' if column is not None else 'disabled')
  column=self.tree.identify_column(event.x)
  if column and column not in self.columns():
   try:column=self.columns()[int(column[1:])]
   except (ValueError,IndexError):column=None
  if column:menu.add_separator();menu.add_command(label='Sort this category',command=lambda:self.sort(column))
  try:menu.tk_popup(event.x_root,event.y_root)
  finally:menu.grab_release()

def enhance_tree(tree):
 if getattr(tree,'_tool_sorter',None):return
 style=ttk.Style(tree);style.configure('ToolWindow.Treeview.Heading',background='#1466ac',foreground='white',font=('Segoe UI',10,'bold'))
 style.map('ToolWindow.Treeview.Heading',background=[('active','#2585ce')],foreground=[('active','white')])
 tree.configure(style='ToolWindow.Treeview');sorter=TableSorter(tree);tree._tool_sorter=sorter
 for column in sorter.columns():
  title=tree.heading(column,'text')
  if title:tree.heading(column,text=title+' ▾',command=lambda c=column:sorter.sort(c))
 # Preserve existing item menus; add sorting only on a category header.
 def context(event):
  if tree.identify_region(event.x,event.y)=='heading':sorter.menu(event);return 'break'
 tree.bind('<Button-3>',context,add='+')


def create_embedded_tab(owner,notebook):
 shell=ttk.Frame(notebook,style='Panel.TFrame');canvas=tk.Canvas(shell,highlightthickness=0,bd=0,bg='white')
 sy=ttk.Scrollbar(shell,command=canvas.yview);sy.pack(side='right',fill='y')
 sx=ttk.Scrollbar(shell,orient='horizontal',command=canvas.xview);sx.pack(side='bottom',fill='x')
 canvas.pack(fill='both',expand=True);canvas.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
 content=ttk.Frame(canvas,style='Panel.TFrame',padding=12);content._scroll_canvas=canvas
 item=canvas.create_window(0,0,window=content,anchor='nw')
 def fit(e=None):
  canvas.itemconfigure(item,width=max(canvas.winfo_width(),content.winfo_reqwidth()))
  canvas.configure(scrollregion=canvas.bbox('all'))
 canvas.bind('<Configure>',fit);content.bind('<Configure>',fit)
 install_router(shell.winfo_toplevel());return shell,content

def install_deferred(cls):
 original=cls.__init__
 def init(self,*args,**kwargs):
  original(self,*args,**kwargs);self._parent._embedded_deferred=self
 cls.__init__=init

def install_explorer(cls):
 original_init=cls.__init__;original_record=cls.record
 def init(self,*args,**kwargs):
  original_init(self,*args,**kwargs);self._route_history=[];self._route_index=-1;self._route_moving=False
  # Explorer chrome operates on the embedded tool, never a separate window.
  self.canvas.grid_configure(row=1);self.xscroll.grid_configure(row=2);self.yscroll.grid_configure(row=1);self.frame.rowconfigure(0,weight=0);self.frame.rowconfigure(1,weight=1)
  from explorer_bar_ui import build_bar
  build_bar(self,lambda:home(self),lambda:fullscreen(self),lambda:close_current(self),lambda direction:navigate(self,direction),lambda:sort_current(self))
  root=self.frame.winfo_toplevel();root.bind('<Escape>',lambda e:root.attributes('-fullscreen',False),add='+');install_router(root)
 def record(self):
  original_record(self);route=self.selected_route()
  if not route or route[0][2]=='Home' or self._route_moving:return
  key=tool_key(route)
  if self._route_index>=0 and tool_key(self._route_history[self._route_index])==key:return
  del self._route_history[self._route_index+1:];self._route_history.append(list(route));self._route_index=len(self._route_history)-1
 def home(self):
  for tab in self.notebook.tabs():
   if self.notebook.tab(tab,'text').strip()=='Home':self.notebook.select(tab);break
 def navigate(self,direction):
  index=self._route_index+direction
  if not 0<=index<len(self._route_history):return
  self._route_moving=True;self._route_index=index
  try:
   for book,tab,label in self._route_history[index]:book.select(tab)
  finally:self.frame.after_idle(lambda:setattr(self,'_route_moving',False))
 def fullscreen(self):
  root=self.frame.winfo_toplevel();root.attributes('-fullscreen',not bool(root.attributes('-fullscreen')))
 def close_route(self,route):
  for book,tab,label in reversed(route):
   deferred=getattr(book.nametowidget(tab),'_embedded_deferred',None)
   if deferred is not None and deferred._loaded:
    content=getattr(deferred,'_content_parent',None)
    if content is not None:content.destroy()
    deferred._tool=None;deferred._loaded=False
    deferred._binding=deferred._parent.bind('<Map>',deferred._mapped,add='+')
    break
  owner=getattr(self,'owner',None)
  if owner is not None and route and route[0][2] in ('Image','Photos') and getattr(owner,'is_processing',False):owner.stop_processing()
 def close_current(self):
  route=self.selected_route();key=tool_key(route)
  close_route(self,route);self.entries.pop(key,None)
  self._route_history=[r for r in self._route_history if tool_key(r)!=key];self._route_index=min(self._route_index,len(self._route_history)-1)
  home(self);self.draw()
 def close_all(self):
  if self.pending is not None:
   try:self.frame.after_cancel(self.pending)
   except tk.TclError:pass
  self.pending=None
  for entry in list(self.entries.values()):close_route(self,entry['route'])
  self.entries.clear();self.hits=[];self.photos=[];self._route_history=[];self._route_index=-1;self.last_key=None;self.hide_tip();home(self);self.canvas.delete('all');self.draw()
 def reopen(self,entry):
  for book,tab,label in entry['route']:book.select(tab)
  self.schedule()
 def remove(self,items):
  selected=tool_key(self.selected_route());removed=set()
  for entry in items:
   key=tool_key(entry['route']);removed.add(key);close_route(self,entry['route']);self.entries.pop(key,None)
  self._route_history=[r for r in self._route_history if tool_key(r) not in removed];self._route_index=min(self._route_index,len(self._route_history)-1)
  if selected in removed:home(self)
  self.draw()
 def sort_current(self):
  route=self.selected_route()
  if not route:return
  book,tab,label=route[-1];page=book.nametowidget(tab);trees=[]
  def walk(w):
   for child in w.winfo_children():
    if isinstance(child,ttk.Treeview) and child.winfo_viewable():trees.append(child)
    walk(child)
  walk(page);menu=tk.Menu(self.frame,tearoff=False)
  if trees:
   tree=trees[0];enhance_tree(tree);sorter=tree._tool_sorter
   for field in SORT_FIELDS:
    col=sorter.field_column(field);menu.add_command(label='Sort by '+field,state='normal' if col is not None else 'disabled',command=lambda c=col,f=field:sorter.sort(c,f))
  else:menu.add_command(label='This tool has no sortable table',state='disabled')
  try:menu.tk_popup(self.frame.winfo_rootx()+200,self.frame.winfo_rooty())
  finally:menu.grab_release()
 cls.__init__=init;cls.record=record;cls.close_all=close_all;cls.reopen=reopen;cls.remove=remove
