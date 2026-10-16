"""Atomic Explorer icon removal, independent of optional tool teardown."""
import tkinter as tk

def key(route):return tuple(tab for book,tab,label in route[:2])
def route(explorer):
 try:return explorer.selected_route()
 except (tk.TclError,AttributeError):return []
def cancel_pending(explorer):
 job=getattr(explorer,'pending',None)
 if job is not None:
  try:explorer.frame.after_cancel(job)
  except tk.TclError:pass
 explorer.pending=None

def home(explorer):
 for tab in explorer.notebook.tabs():
  if explorer.notebook.tab(tab,'text').strip()=='Home':explorer.notebook.select(tab);return True
 return False

def dismiss(explorer):
 switcher=getattr(explorer,'_switcher',None)
 if switcher is not None:switcher.hide()
 search=getattr(explorer,'_tool_search',None)
 if search is not None:search.hide()
 try:explorer.hide_tip()
 except tk.TclError:pass

def remove_icons(explorer,items,all_icons=False):
 explorer._explorer_close_busy=True
 try:
  cancel_pending(explorer);current=key(route(explorer));removed=set(explorer.entries) if all_icons else set()
  for item in items:
   itemkey=key(item['route']) if isinstance(item,dict) else item
   removed.add(itemkey)
  # Remove entries before any navigation/paint callback can run.
  for itemkey in removed:explorer.entries.pop(itemkey,None)
  if all_icons:explorer.entries.clear()
  dismiss(explorer)
  if hasattr(explorer,'_route_history'):
   explorer._route_history=[r for r in explorer._route_history if key(r) not in removed]
   explorer._route_index=min(explorer._route_index,len(explorer._route_history)-1)
  if all_icons or current in removed:
   explorer._explorer_blocked_key=current
   if home(explorer):explorer._explorer_blocked_key=None
  explorer.last_key=key(route(explorer));cancel_pending(explorer)
  explorer.hits=[];explorer.photos=[];explorer.canvas.delete('all')
  if all_icons:
   explorer.canvas.xview_moveto(0);explorer.canvas.yview_moveto(0)
  explorer.draw()
 finally:explorer._explorer_close_busy=False

def close_active(explorer):
 current=key(route(explorer));entry=explorer.entries.get(current)
 if entry is not None:remove_icons(explorer,[entry])
 else:
  # No active dock entry: clear any stale hit/overlay state safely.
  cancel_pending(explorer);explorer.hits=[];explorer.photos=[];explorer.canvas.delete('all');explorer.draw()

def install(cls):
 original_record=cls.record
 def record(self):
  self.pending=None
  if getattr(self,'_explorer_close_busy',False):return
  current=route(self)
  blocked=getattr(self,'_explorer_blocked_key',None)
  if blocked is not None:
   if key(current)==blocked:self.draw();return
   self._explorer_blocked_key=None
  return original_record(self)
 def remove(self,items):remove_icons(self,items)
 def close_all(self):remove_icons(self,[],True)
 cls.record=record;cls.remove=remove;cls.close_all=close_all
