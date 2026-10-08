"""Preview-first, collision-safe asset sorter for AI Generator."""
import os
import shutil
import threading
import tkinter as tk
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk


MODEL_EXTS={'.fbx','.obj','.ascii','.smd','.dae','.cast','.psx','.gltf','.glb','.3ds','.blend','.ply','.stl','.x','.nif','.mesh','.md5mesh'}
ANIMATION_EXTS={'.psa','.anim','.anm','.animation','.hkx','.bvh','.md5anim','.vmd','.mocap'}
AMBIGUOUS_EXTS={'.fbx','.smd','.cast'}
TEXTURE_EXTS={'.dds','.png','.jpg','.jpeg','.tga','.bmp','.gif','.tif','.tiff','.webp','.ktx','.ktx2','.pvr','.hdr','.exr','.pcx','.psd','.xcf','.svg','.ico','.jp2','.j2k','.astc','.basis','.txd'}
SOUND_EXTS={'.wav','.mp3','.ogg','.flac','.aac','.m4a','.wma','.aiff','.aif','.opus','.ac3','.mid','.midi','.xm','.mod','.s3m','.it','.at3','.vag','.adx'}
CATEGORIES=('Models','Textures','Animations','Sounds')


@dataclass
class SortItem:
    source:str
    category:str
    destination:str
    reason:str


def friendly_size(value):
    size=float(value)
    for unit in ('B','KB','MB','GB','TB'):
        if size<1024 or unit=='TB':return f'{size:.0f} {unit}' if unit=='B' else f'{size:.1f} {unit}'
        size/=1024


class SortTool:
    def __init__(self,parent):
        self.parent=parent;self.root_dir=tk.StringVar();self.status=tk.StringVar(value='Choose a directory to preview sorting.');self.progress=tk.DoubleVar();self.plan=[];self.running=False;self._build()
    def _build(self):
        self.parent.grid_columnconfigure(0,weight=1);self.parent.grid_rowconfigure(2,weight=1)
        top=ttk.Frame(self.parent,padding=(8,6));top.grid(row=0,column=0,sticky='ew');top.columnconfigure(1,weight=1);ttk.Label(top,text='Directory').grid(row=0,column=0,sticky='w');ttk.Entry(top,textvariable=self.root_dir).grid(row=0,column=1,sticky='ew',padx=7);ttk.Button(top,text='Browse',command=self.browse).grid(row=0,column=2);self.preview_button=ttk.Button(top,text='Preview Sort',command=self.preview);self.preview_button.grid(row=0,column=3,padx=(6,0));self.run_button=ttk.Button(top,text='Move + Create ZIP',command=self.run,state='disabled');self.run_button.grid(row=0,column=4,padx=(6,0))
        note=ttk.Label(self.parent,text='Preview first. Folder structure is preserved. Existing files are never replaced; conflicts receive numbered names. Unknown file types always ask for a category or Skip.',wraplength=950);note.grid(row=1,column=0,sticky='ew',padx=8,pady=(0,5))
        holder=ttk.Frame(self.parent);holder.grid(row=2,column=0,sticky='nsew',padx=8);holder.rowconfigure(0,weight=1);holder.columnconfigure(0,weight=1);self.tree=ttk.Treeview(holder,columns=('source','category','destination','size','reason'),show='headings');
        for key,title,width in (('source','Source',280),('category','Folder',90),('destination','Destination',330),('size','Size',80),('reason','Rule',180)):self.tree.heading(key,text=title);self.tree.column(key,width=width,anchor='w')
        sy=ttk.Scrollbar(holder,orient='vertical',command=self.tree.yview);sx=ttk.Scrollbar(holder,orient='horizontal',command=self.tree.xview);self.tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);self.tree.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew')
        bottom=ttk.Frame(self.parent,padding=8);bottom.grid(row=3,column=0,sticky='ew');bottom.columnconfigure(0,weight=1);ttk.Progressbar(bottom,variable=self.progress,maximum=100,style='Accent.Horizontal.TProgressbar').grid(row=0,column=0,sticky='ew');ttk.Label(bottom,textvariable=self.status).grid(row=1,column=0,sticky='w',pady=(4,0))
    def browse(self):
        path=filedialog.askdirectory(title='Choose directory to sort')
        if path:self.root_dir.set(path);self.plan=[];self.run_button.config(state='disabled')
    def preview(self):
        root=os.path.abspath(self.root_dir.get().strip())
        if not os.path.isdir(root):messagebox.showwarning('Sort','Choose a valid directory.');return
        self.preview_button.config(state='disabled');self.run_button.config(state='disabled');self.status.set('Scanning files…');self.parent.update_idletasks()
        try:self.plan=self.build_plan(root);self.show_plan(root);self.run_button.config(state='normal' if self.plan else 'disabled');self.status.set(f'Preview ready: {len(self.plan):,} files. Nothing has been moved.')
        except Exception as error:messagebox.showerror('Sort preview',str(error));self.status.set('Preview failed.')
        finally:self.preview_button.config(state='normal')
    def build_plan(self,root):
        sources=[];ignored=set(CATEGORIES)
        for directory,folders,files in os.walk(root):
            relative=os.path.relpath(directory,root);top=relative.split(os.sep)[0] if relative!='.' else ''
            folders[:]=[name for name in folders if name not in ignored and not name.startswith('.')]
            if top in ignored:continue
            for name in files:
                if name.lower().startswith('extracted') and name.lower().endswith('.zip'):continue
                path=os.path.join(directory,name);sources.append(path)
        groups=defaultdict(list)
        for path in sources:groups[os.path.splitext(os.path.basename(path))[0].lower()].append(path)
        classification={};reasons={};anim_numbers=defaultdict(int)
        for stem,paths in groups.items():
            ambiguous=[p for p in paths if os.path.splitext(p)[1].lower() in AMBIGUOUS_EXTS]
            if len(ambiguous)>1:
                ordered=sorted(ambiguous,key=lambda p:os.path.getsize(p),reverse=True);classification[ordered[0]]='Models';reasons[ordered[0]]='largest same-name model'
                for path in ordered[1:]:classification[path]='Animations';reasons[path]='smaller same-name animation';anim_numbers[stem]+=1
        for path in sources:
            if path in classification:continue
            ext=os.path.splitext(path)[1].lower()
            if ext in ANIMATION_EXTS:category,reason='Animations','animation extension'
            elif ext in TEXTURE_EXTS:category,reason='Textures','texture extension'
            elif ext in SOUND_EXTS:category,reason='Sounds','sound extension'
            elif ext in MODEL_EXTS:category,reason='Models','model extension'
            else:
                category=self.ask_unknown(path,ext)
                if category=='Skip':continue
                reason='user classified unknown type'
            classification[path]=category;reasons[path]=reason
        reserved=set();plan=[];anim_counts=defaultdict(int)
        for path in sorted(classification,key=str.lower):
            category=classification[path];relative_parent=os.path.relpath(os.path.dirname(path),root);relative_parent='' if relative_parent=='.' else relative_parent;name=os.path.basename(path);stem,ext=os.path.splitext(name)
            if reasons[path]=='smaller same-name animation':anim_counts[stem.lower()]+=1;name=f'{stem}_anim_{anim_counts[stem.lower()]}{ext}'
            target_dir=os.path.join(root,category,relative_parent);destination=self.unique_path(os.path.join(target_dir,name),reserved);reserved.add(os.path.normcase(destination));plan.append(SortItem(path,category,destination,reasons[path]))
        return plan
    def ask_unknown(self,path,ext):
        dialog=tk.Toplevel(self.parent);dialog.title('Unknown file type');dialog.transient(self.parent.winfo_toplevel());dialog.grab_set();choice=tk.StringVar(value='Skip');ttk.Label(dialog,text=f'Choose where this unknown file belongs:\n{path}\nExtension: {ext or "(none)"}',wraplength=560,padding=14).pack(fill='x');box=ttk.Combobox(dialog,textvariable=choice,values=CATEGORIES+('Skip',),state='readonly');box.pack(padx=14,fill='x');ttk.Button(dialog,text='Continue',command=dialog.destroy).pack(pady=14);dialog.protocol('WM_DELETE_WINDOW',dialog.destroy);self.parent.wait_window(dialog);return choice.get()
    @staticmethod
    def unique_path(path,reserved):
        if not os.path.exists(path) and os.path.normcase(path) not in reserved:return path
        stem,ext=os.path.splitext(path);number=2
        while True:
            candidate=f'{stem}_{number}{ext}'
            if not os.path.exists(candidate) and os.path.normcase(candidate) not in reserved:return candidate
            number+=1
    def show_plan(self,root):
        self.tree.delete(*self.tree.get_children())
        for item in self.plan:self.tree.insert('', 'end',values=(os.path.relpath(item.source,root),item.category,os.path.relpath(item.destination,root),friendly_size(os.path.getsize(item.source)),item.reason))
    def run(self):
        if not self.plan or self.running:return
        if not messagebox.askyesno('Sort files',f'Move {len(self.plan):,} files and build the ZIP?\n\nExisting files will never be overwritten.'):return
        self.running=True;self.preview_button.config(state='disabled');self.run_button.config(state='disabled');threading.Thread(target=self.worker,daemon=True).start()
    def worker(self):
        root=os.path.abspath(self.root_dir.get().strip());moved=0;errors=[];total=max(1,len(self.plan))
        for index,item in enumerate(self.plan,1):
            try:
                if not os.path.isfile(item.source):raise FileNotFoundError('source no longer exists')
                os.makedirs(os.path.dirname(item.destination),exist_ok=True);destination=self.unique_path(item.destination,set());shutil.move(item.source,destination);moved+=1
            except Exception as error:errors.append(f'{item.source}: {error}')
            percent=index/total*80;self.parent.after(0,lambda p=percent,n=index:self.update_progress(p,f'Moving {n:,} of {total:,}…'))
        archive=self.unique_path(os.path.join(root,'Extracted.zip'),set())
        try:
            self.parent.after(0,lambda:self.update_progress(85,'Creating archive…'))
            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,allowZip64=True) as output:
                for category in CATEGORIES:
                    base=os.path.join(root,category)
                    if not os.path.isdir(base):continue
                    for directory,_folders,files in os.walk(base):
                        for name in files:
                            path=os.path.join(directory,name);output.write(path,os.path.relpath(path,root))
        except Exception as error:errors.append(f'Archive: {error}')
        self.parent.after(0,lambda:self.done(moved,archive,errors))
    def update_progress(self,value,text):self.progress.set(value);self.status.set(text)
    def done(self,moved,archive,errors):
        self.running=False;self.progress.set(100);self.preview_button.config(state='normal');self.status.set(f'Moved {moved:,} files. Archive: {os.path.basename(archive)}. Errors: {len(errors)}');self.plan=[]
        if errors:messagebox.showwarning('Sort complete',self.status.get()+'\n\n'+ '\n'.join(errors[:12]))
        else:messagebox.showinfo('Sort complete',self.status.get())


def build_sort_tool(parent):return SortTool(parent)
