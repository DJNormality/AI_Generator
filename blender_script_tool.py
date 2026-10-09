"""Catalog and optional host runner for Blender and 3DS Max conversion scripts."""
import os, re, subprocess, threading, tkinter as tk, zipfile
from tkinter import filedialog, messagebox, ttk

class BlenderScriptTool:
    def __init__(self,parent):
        self.parent=parent;root=os.path.dirname(os.path.abspath(__file__));self.archives={'Blender':os.path.join(root,'resources','BLENDER.zip'),'3DS Max':os.path.join(root,'resources','3DSMAX.zip')};self.rows=[];self.filtered=[];self.search=tk.StringVar();self.blender=tk.StringVar();self.output=tk.StringVar();self.status=tk.StringVar(value='Script archives are indexed without executing their contents.');self._build();self.index()
    def _build(self):
        self.parent.grid_columnconfigure(0,weight=1);self.parent.grid_rowconfigure(2,weight=1);top=ttk.Frame(self.parent,padding=8);top.grid(row=0,column=0,sticky='ew');top.columnconfigure(1,weight=1);ttk.Label(top,text='Search game / format').grid(row=0,column=0);entry=ttk.Entry(top,textvariable=self.search);entry.grid(row=0,column=1,sticky='ew',padx=5);entry.bind('<KeyRelease>',lambda _e:self.filter());ttk.Button(top,text='Reindex',command=self.index).grid(row=0,column=2)
        paths=ttk.Frame(self.parent,padding=(8,0,8,5));paths.grid(row=1,column=0,sticky='ew');paths.columnconfigure(1,weight=1);ttk.Label(paths,text='Blender executable').grid(row=0,column=0);ttk.Entry(paths,textvariable=self.blender).grid(row=0,column=1,sticky='ew',padx=5);ttk.Button(paths,text='Browse',command=lambda:self.pick(self.blender,False)).grid(row=0,column=2);ttk.Label(paths,text='Output folder').grid(row=1,column=0);ttk.Entry(paths,textvariable=self.output).grid(row=1,column=1,sticky='ew',padx=5);ttk.Button(paths,text='Browse',command=lambda:self.pick(self.output,True)).grid(row=1,column=2)
        body=ttk.Frame(self.parent,padding=(8,0));body.grid(row=2,column=0,sticky='nsew');body.rowconfigure(0,weight=1);body.columnconfigure(0,weight=1);self.tree=ttk.Treeview(body,columns=('host','game','formats','script'),show='headings')
        for key,title,width in (('host','Host',90),('game','Identified game / purpose',260),('formats','Format hints',240),('script','Script',420)):self.tree.heading(key,text=title);self.tree.column(key,width=width,anchor='w')
        sy=ttk.Scrollbar(body,orient='vertical',command=self.tree.yview);self.tree.configure(yscrollcommand=sy.set);self.tree.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns')
        bottom=ttk.Frame(self.parent,padding=8);bottom.grid(row=3,column=0,sticky='ew');ttk.Label(bottom,textvariable=self.status).pack(side='left');ttk.Button(bottom,text='Export Selected Script',command=self.export).pack(side='right');ttk.Button(bottom,text='Run in Blender',command=self.run_blender).pack(side='right',padx=5)
    def pick(self,var,directory):
        value=filedialog.askdirectory() if directory else filedialog.askopenfilename(filetypes=[('Executable','*.exe'),('All files','*.*')])
        if value:var.set(value)
    def index(self):
        rows=[]
        for host,path in self.archives.items():
            if not os.path.isfile(path):continue
            try:
                with zipfile.ZipFile(path) as archive:
                    for name in archive.namelist():
                        if name.endswith('/') or not name.lower().endswith(('.py','.ms','.mcr')):continue
                        title=os.path.splitext(os.path.basename(name))[0];game=re.sub(r'[_-]+',' ',title);formats=self._hints(title)
                        rows.append((host,game,formats,name,path))
            except Exception:pass
        self.rows=rows;self.filter();self.status.set(f'Indexed {len(rows):,} Blender and 3DS Max conversion/reference scripts. No scripts were executed.')
    @staticmethod
    def _hints(text):
        known=('fbx','obj','nif','blend','psa','psk','smd','dae','xml','gr2','dds','tmd','mod','mesh','bin','ascii','anim')
        hits=[value.upper() for value in known if re.search(r'(^|[^a-z])'+re.escape(value)+r'([^a-z]|$)',text,re.I)];return ', '.join(hits) or 'Inspect script'
    def filter(self):
        query=self.search.get().lower().strip();self.filtered=[row for row in self.rows if not query or query in ' '.join(row[:4]).lower()];self.tree.delete(*self.tree.get_children())
        for index,row in enumerate(self.filtered):self.tree.insert('','end',iid=str(index),values=row[:4])
    def selected(self):
        selection=self.tree.selection();return self.filtered[int(selection[0])] if selection else None
    def export(self):
        row=self.selected()
        if not row:messagebox.showwarning('Scripts','Select a script first.');return
        path=filedialog.asksaveasfilename(initialfile=os.path.basename(row[3]))
        if not path:return
        with zipfile.ZipFile(row[4]) as archive,open(path,'wb') as output:output.write(archive.read(row[3]))
        self.status.set(f'Exported {path}')
    def run_blender(self):
        row=self.selected()
        if not row or row[0]!='Blender':messagebox.showwarning('Blender','Select a Blender Python script.');return
        if not os.path.isfile(self.blender.get()):messagebox.showwarning('Blender','Choose a trusted Blender executable.');return
        folder=self.output.get().strip() or os.path.join(os.path.dirname(os.path.abspath(__file__)),'temp_processing','blender_scripts');os.makedirs(folder,exist_ok=True);script=os.path.join(folder,os.path.basename(row[3]))
        with zipfile.ZipFile(row[4]) as archive,open(script,'wb') as output:output.write(archive.read(row[3]))
        self.status.set('Running selected script in Blender. Script compatibility depends on its Blender version and expected inputs.')
        def worker():
            try:completed=subprocess.run([self.blender.get(),'--background','--python',script],capture_output=True,text=True,timeout=3600);message=f'Blender exited {completed.returncode}: '+(completed.stderr[-500:] or completed.stdout[-500:])
            except Exception as error:message=f'Blender error: {error}'
            self.parent.after(0,lambda:self.status.set(message))
        threading.Thread(target=worker,daemon=True).start()

def build_blender_script_tool(parent):return BlenderScriptTool(parent)
