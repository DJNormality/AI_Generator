"""Preview-first file and folder cleanup with filterable tabs."""
from __future__ import annotations
import os, threading, tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

class RemoveTool:
    def __init__(self,parent):
        self.parent=parent;self.folder=tk.StringVar();self.status=tk.StringVar(value='Choose a directory, set filters, and scan. Scanning never removes anything.');self.views={};self._build()
    def _build(self):
        self.parent.grid_columnconfigure(0,weight=1);self.parent.grid_rowconfigure(2,weight=1)
        top=ttk.Frame(self.parent,padding=8);top.grid(row=0,column=0,sticky='ew');top.columnconfigure(1,weight=1);ttk.Label(top,text='Directory').grid(row=0,column=0);ttk.Entry(top,textvariable=self.folder).grid(row=0,column=1,sticky='ew',padx=6);ttk.Button(top,text='Browse',command=self.browse).grid(row=0,column=2)
        tabs=ttk.Notebook(self.parent,style='Modern.TNotebook');tabs.grid(row=2,column=0,sticky='nsew',padx=8);folders=ttk.Frame(tabs,style='Panel.TFrame');files=ttk.Frame(tabs,style='Panel.TFrame');tabs.add(folders,text='  Folders  ');tabs.add(files,text='  Files  ')
        self._build_tab(folders,'folders');self._build_tab(files,'files')
        bottom=ttk.Frame(self.parent,padding=8);bottom.grid(row=3,column=0,sticky='ew');ttk.Label(bottom,textvariable=self.status).pack(side='left')
    def _build_tab(self,parent,kind):
        parent.columnconfigure(0,weight=1);parent.rowconfigure(1,weight=1)
        name=tk.StringVar();type_value=tk.StringVar(value='Empty folders' if kind=='folders' else 'All files');minimum=tk.StringVar();maximum=tk.StringVar(value='' if kind=='folders' else '1');date_from=tk.StringVar();date_to=tk.StringVar()
        filters=ttk.Frame(parent,padding=(4,7));filters.grid(row=0,column=0,sticky='ew')
        ttk.Label(filters,text='Name').pack(side='left');ttk.Entry(filters,textvariable=name,width=15).pack(side='left',padx=(4,10))
        ttk.Label(filters,text='Type').pack(side='left')
        if kind=='folders':ttk.Combobox(filters,textvariable=type_value,values=('Empty folders','Non-empty folders','All folders'),state='readonly',width=17).pack(side='left',padx=(4,10))
        else:ttk.Entry(filters,textvariable=type_value,width=14).pack(side='left',padx=(4,10))
        ttk.Label(filters,text='Size KB').pack(side='left');ttk.Entry(filters,textvariable=minimum,width=7).pack(side='left',padx=(4,2));ttk.Label(filters,text='to').pack(side='left');ttk.Entry(filters,textvariable=maximum,width=7).pack(side='left',padx=(2,10))
        ttk.Label(filters,text='Date').pack(side='left');ttk.Entry(filters,textvariable=date_from,width=11).pack(side='left',padx=(4,2));ttk.Label(filters,text='to').pack(side='left');ttk.Entry(filters,textvariable=date_to,width=11).pack(side='left',padx=(2,10))
        ttk.Button(filters,text='Scan',command=lambda:self.scan(kind)).pack(side='left');ttk.Button(filters,text='Select All',command=lambda:self.select_all(kind)).pack(side='left',padx=5);ttk.Button(filters,text='Remove Selected',command=lambda:self.remove_selected(kind)).pack(side='left')
        body=ttk.Frame(parent);body.grid(row=1,column=0,sticky='nsew');body.rowconfigure(0,weight=1);body.columnconfigure(0,weight=1);tree=ttk.Treeview(body,columns=('name','type','size','date','path'),show='headings',selectmode='extended')
        for key,title,width in (('name','Name',180),('type','Type',110),('size','Size',100),('date','Date',150),('path','Path',520)):tree.heading(key,text=title);tree.column(key,width=width,anchor='w')
        sy=ttk.Scrollbar(body,orient='vertical',command=tree.yview);sx=ttk.Scrollbar(body,orient='horizontal',command=tree.xview);tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);tree.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew')
        hint='Type: Empty, Non-empty, or All. Blank size/date limits include everything.' if kind=='folders' else 'Type accepts an extension such as .jpg, png, wav, or All files. Dates use YYYY-MM-DD.'
        ttk.Label(parent,text=hint,style='Hint.TLabel').grid(row=2,column=0,sticky='w',pady=(5,2))
        self.views[kind]={'tree':tree,'items':[],'name':name,'type':type_value,'min':minimum,'max':maximum,'from':date_from,'to':date_to}
    def browse(self):
        path=filedialog.askdirectory(title='Choose cleanup directory')
        if path:self.folder.set(path)
    @staticmethod
    def _number(value):
        value=value.strip();return None if not value else max(0,float(value))*1024
    @staticmethod
    def _date(value,end=False):
        value=value.strip()
        if not value:return None
        parsed=datetime.strptime(value,'%Y-%m-%d');return parsed.timestamp()+86399.999 if end else parsed.timestamp()
    def scan(self,kind):
        root=os.path.abspath(self.folder.get().strip());view=self.views[kind];tree=view['tree'];tree.delete(*tree.get_children());view['items']=[]
        if not os.path.isdir(root):messagebox.showwarning('Remove','Choose a valid directory.');return
        try:filters={'name':view['name'].get().strip().lower(),'type':view['type'].get().strip().lower(),'min':self._number(view['min'].get()),'max':self._number(view['max'].get()),'from':self._date(view['from'].get()),'to':self._date(view['to'].get(),True)}
        except ValueError:messagebox.showerror('Remove','Size must be a number and dates must use YYYY-MM-DD.');return
        self.status.set(f'Scanning {kind}…');threading.Thread(target=self._scan_worker,args=(root,kind,filters),daemon=True).start()
    def _scan_worker(self,root,kind,filters):
        found=[];folder_sizes={};folder_counts={}
        for current,dirs,files in os.walk(root,topdown=False):
            total=0;count=len(files)
            for filename in files:
                path=os.path.join(current,filename)
                try:size=os.path.getsize(path);modified=os.path.getmtime(path)
                except OSError:continue
                total+=size
                if kind=='files':
                    extension=os.path.splitext(filename)[1].lower();type_filter=filters['type'].lstrip('.')
                    if filters['type'] not in ('','all','all files','*','*.*') and extension.lstrip('.')!=type_filter:continue
                    if self._matches(filename,size,modified,filters):found.append({'name':filename,'type':extension or 'File','size':size,'date':modified,'path':path,'folder':False})
            for directory in dirs:
                child=os.path.join(current,directory);total+=folder_sizes.get(child,0);count+=folder_counts.get(child,0)
            folder_sizes[current]=total;folder_counts[current]=count
            if kind=='folders' and current!=root:
                folder_type='Empty folder' if count==0 else 'Folder';requested=filters['type']
                if requested=='empty folders' and count!=0:continue
                if requested=='non-empty folders' and count==0:continue
                try:modified=os.path.getmtime(current)
                except OSError:continue
                if self._matches(os.path.basename(current),total,modified,filters):found.append({'name':os.path.basename(current),'type':folder_type,'size':total,'date':modified,'path':current,'folder':True})
        found.sort(key=lambda item:(item['date'],item['name'].lower()),reverse=True);self.parent.after(0,lambda:self._show(kind,found))
    @staticmethod
    def _matches(name,size,modified,filters):
        return (not filters['name'] or filters['name'] in name.lower()) and (filters['min'] is None or size>=filters['min']) and (filters['max'] is None or size<=filters['max']) and (filters['from'] is None or modified>=filters['from']) and (filters['to'] is None or modified<=filters['to'])
    def _show(self,kind,items):
        view=self.views[kind];view['items']=items;tree=view['tree']
        for index,item in enumerate(items):tree.insert('','end',iid=str(index),values=(item['name'],item['type'],self._size(item['size']),datetime.fromtimestamp(item['date']).strftime('%Y-%m-%d %H:%M'),item['path']))
        self.status.set(f'Found {len(items):,} matching {kind}. Review and select items before removing.')
    def select_all(self,kind):
        tree=self.views[kind]['tree'];tree.selection_set(tree.get_children())
    def remove_selected(self,kind):
        view=self.views[kind];tree=view['tree'];selected=[int(item) for item in tree.selection()]
        if not selected:messagebox.showwarning('Remove',f'Select {kind} first.');return
        try:from send2trash import send2trash
        except Exception:send2trash=None
        warning=f'Move {len(selected)} selected {kind} to the Recycle Bin?' if send2trash else f'Permanently remove {len(selected)} selected {kind}? Non-empty folders cannot be permanently removed by this fallback.'
        if not messagebox.askyesno('Confirm removal',warning):return
        removed=failed=0
        for index in sorted(selected,reverse=True):
            item=view['items'][index];path=item['path']
            try:
                if send2trash:send2trash(path)
                elif item['folder']:os.rmdir(path)
                else:os.remove(path)
                removed+=1;tree.delete(str(index))
            except Exception:failed+=1
        self.status.set(f'Removed {removed}; failed {failed}. '+('Moved to Recycle Bin.' if send2trash else 'Permanent fallback used.'))
    @staticmethod
    def _size(value):
        units=('B','KB','MB','GB','TB');amount=float(value)
        for unit in units:
            if amount<1024 or unit==units[-1]:return f'{amount:.0f} {unit}' if unit=='B' else f'{amount:.2f} {unit}'
            amount/=1024

def build_remove_tool(parent):return RemoveTool(parent)
