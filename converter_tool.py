"""Script-driven batch converter embedded in AI Generator's Files tab."""
import importlib.util
import os
import threading
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


FILTERS = {
    'All PNG, JPG, and WebP': {'.png', '.jpg', '.jpeg', '.webp'},
    'Only PNG': {'.png'},
    'Only JPG / JPEG': {'.jpg', '.jpeg'},
    'Only WebP': {'.webp'},
    'PNG and JPG': {'.png', '.jpg', '.jpeg'},
    'PNG and WebP': {'.png', '.webp'},
    'JPG and WebP': {'.jpg', '.jpeg', '.webp'},
}


class ConverterTool:
    def __init__(self, parent):
        self.parent = parent
        self.script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Python', 'Coverters')
        self.converters = {}
        self.stop_event = threading.Event()
        self.worker = None
        self._build()
        self.reload_scripts()

    def _build(self):
        shell = ttk.Frame(self.parent, padding=12);shell.pack(fill='both', expand=True)
        shell.columnconfigure(1, weight=1);shell.rowconfigure(8, weight=1)
        self.input_dir=tk.StringVar();self.output_dir=tk.StringVar();self.filter_name=tk.StringVar(value='All PNG, JPG, and WebP')
        self.script_name=tk.StringVar();self.dds_format=tk.StringVar(value='Uncompressed RGBA')
        self.archive_script=tk.StringVar();self.archive_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','PYTHON.zip');self.archive_members=[]
        self.recursive=tk.BooleanVar(value=False);self.preserve_structure=tk.BooleanVar(value=True);self.overwrite=tk.BooleanVar(value=False)
        self.progress=tk.DoubleVar(value=0);self.progress_text=tk.StringVar(value='0%');self.status=tk.StringVar(value='Load folders and choose Convert.')
        ttk.Label(shell,text='Python converter scripts',font=('Segoe UI Semibold',13)).grid(row=0,column=0,columnspan=3,sticky='w')
        ttk.Label(shell,text=r'Scripts are discovered from Python\Coverters. Only place trusted Python scripts in this folder.',wraplength=900).grid(row=1,column=0,columnspan=3,sticky='w',pady=(2,10))
        self._path_row(shell,2,'Input folder',self.input_dir,self.choose_input)
        self._path_row(shell,3,'Output folder',self.output_dir,self.choose_output)
        ttk.Label(shell,text='Input types').grid(row=4,column=0,sticky='w',pady=5)
        ttk.Combobox(shell,textvariable=self.filter_name,values=tuple(FILTERS),state='readonly').grid(row=4,column=1,sticky='ew',pady=5)
        ttk.Label(shell,text='Converter script').grid(row=5,column=0,sticky='w',pady=5)
        script_row=ttk.Frame(shell);script_row.grid(row=5,column=1,columnspan=2,sticky='ew',pady=5);script_row.columnconfigure(0,weight=1)
        self.script_combo=ttk.Combobox(script_row,textvariable=self.script_name,state='readonly');self.script_combo.grid(row=0,column=0,sticky='ew')
        ttk.Button(script_row,text='Reload Scripts',command=self.reload_scripts).grid(row=0,column=1,padx=(6,0))
        ttk.Label(shell,text='Python archive').grid(row=6,column=0,sticky='w',pady=5);archive_row=ttk.Frame(shell);archive_row.grid(row=6,column=1,columnspan=2,sticky='ew');archive_row.columnconfigure(0,weight=1);self.archive_combo=ttk.Combobox(archive_row,textvariable=self.archive_script,state='readonly');self.archive_combo.grid(row=0,column=0,sticky='ew');ttk.Button(archive_row,text='Load Archive',command=self.choose_archive).grid(row=0,column=1,padx=5);ttk.Button(archive_row,text='Extract Selected',command=self.extract_archive_script).grid(row=0,column=2)
        ttk.Label(shell,text='DDS format').grid(row=7,column=0,sticky='w',pady=5)
        ttk.Combobox(shell,textvariable=self.dds_format,values=('Uncompressed RGBA','DXT1 / BC1','DXT3 / BC2','DXT5 / BC3','BC5'),state='readonly').grid(row=7,column=1,sticky='ew',pady=5)
        options=ttk.Frame(shell);options.grid(row=7,column=2,sticky='e',padx=(12,0))
        ttk.Checkbutton(options,text='Subfolders',variable=self.recursive).pack(side='left')
        ttk.Checkbutton(options,text='Keep structure',variable=self.preserve_structure).pack(side='left',padx=8)
        ttk.Checkbutton(options,text='Overwrite',variable=self.overwrite).pack(side='left')
        results=ttk.Frame(shell);results.grid(row=8,column=0,columnspan=3,sticky='nsew',pady=(8,6));results.rowconfigure(0,weight=1);results.columnconfigure(0,weight=1)
        self.tree=ttk.Treeview(results,columns=('source','result','status'),show='headings')
        for key,title,width in (('source','Source',330),('result','DDS Output',330),('status','Status',180)):self.tree.heading(key,text=title);self.tree.column(key,width=width,anchor='w')
        sy=ttk.Scrollbar(results,orient='vertical',command=self.tree.yview);self.tree.configure(yscrollcommand=sy.set);self.tree.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns')
        bottom=ttk.Frame(shell);bottom.grid(row=9,column=0,columnspan=3,sticky='ew');bottom.columnconfigure(0,weight=1)
        ttk.Progressbar(bottom,variable=self.progress,maximum=100,style='Accent.Horizontal.TProgressbar').grid(row=0,column=0,sticky='ew')
        ttk.Label(bottom,textvariable=self.progress_text,width=6).grid(row=0,column=1,padx=6)
        self.convert_button=ttk.Button(bottom,text='Convert to DDS',command=self.start);self.convert_button.grid(row=0,column=2)
        self.stop_button=ttk.Button(bottom,text='Stop',command=self.stop,state='disabled');self.stop_button.grid(row=0,column=3,padx=(6,0))
        ttk.Label(bottom,textvariable=self.status).grid(row=1,column=0,columnspan=4,sticky='w',pady=(4,0))

    def _path_row(self,parent,row,label,var,command):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky='w',pady=5)
        ttk.Entry(parent,textvariable=var).grid(row=row,column=1,sticky='ew',pady=5)
        ttk.Button(parent,text='Browse',command=command).grid(row=row,column=2,padx=(6,0),pady=5)

    def choose_input(self):
        value=filedialog.askdirectory(title='Select image input folder')
        if value:self.input_dir.set(value)
    def choose_output(self):
        value=filedialog.askdirectory(title='Select DDS output folder')
        if value:self.output_dir.set(value)

    def reload_scripts(self):
        self.converters={};os.makedirs(self.script_dir,exist_ok=True)
        errors=[]
        for path in sorted(Path(self.script_dir).glob('*.py')):
            if path.name.startswith('_'):continue
            try:
                spec=importlib.util.spec_from_file_location('ai_generator_converter_'+path.stem,str(path));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
                if not callable(getattr(module,'convert_file',None)):raise RuntimeError('missing convert_file()')
                info=getattr(module,'CONVERTER_INFO',{});name=str(info.get('name') or path.stem)
                self.converters[name]=module
            except Exception as error:errors.append(f'{path.name}: {error}')
        names=tuple(self.converters);self.script_combo.configure(values=names)
        if names and self.script_name.get() not in self.converters:self.script_name.set(names[0])
        self.status.set(f'Loaded {len(names)} converter script(s) from Python\\Coverters.'+(f' Errors: {len(errors)}' if errors else ''))
        if os.path.isfile(self.archive_path):self.load_archive(self.archive_path)
    def choose_archive(self):
        path=filedialog.askopenfilename(title='Select Python script archive',filetypes=[('ZIP archive','*.zip')])
        if path:self.archive_path=path;self.load_archive(path)
    def load_archive(self,path):
        try:
            with zipfile.ZipFile(path) as archive:self.archive_members=[name for name in archive.namelist() if name.lower().endswith('.py') and not name.endswith('/')]
            self.archive_combo.configure(values=self.archive_members)
            if self.archive_members:self.archive_script.set(self.archive_members[0])
            self.status.set(f'Indexed {len(self.archive_members):,} Python conversion/reference scripts. Scripts are not executed automatically.')
        except Exception as error:self.status.set(f'Python archive error: {error}')
    def extract_archive_script(self):
        member=self.archive_script.get()
        if not member or not os.path.isfile(self.archive_path):return
        try:
            target_dir=os.path.join(self.script_dir,'Imported');os.makedirs(target_dir,exist_ok=True);target=os.path.join(target_dir,os.path.basename(member))
            with zipfile.ZipFile(self.archive_path) as archive:data=archive.read(member)
            with open(target,'wb') as output:output.write(data)
            self.status.set(f'Extracted as reference: {target}. It is not run unless adapted to convert_file().')
        except Exception as error:messagebox.showerror('Python archive',str(error))

    def files(self):
        root=Path(self.input_dir.get());extensions=FILTERS[self.filter_name.get()]
        iterator=root.rglob('*') if self.recursive.get() else root.glob('*')
        return [path for path in iterator if path.is_file() and path.suffix.lower() in extensions]

    def start(self):
        source=Path(self.input_dir.get());target=Path(self.output_dir.get());module=self.converters.get(self.script_name.get())
        if not source.is_dir():messagebox.showwarning('Convert','Select a valid input folder.');return
        if not self.output_dir.get().strip():messagebox.showwarning('Convert','Select an output folder.');return
        if module is None:messagebox.showwarning('Convert',r'No converter script is loaded from Python\Coverters.');return
        images=self.files()
        if not images:messagebox.showwarning('Convert','No matching PNG, JPG, JPEG, or WebP files were found.');return
        self.tree.delete(*self.tree.get_children());self.stop_event.clear();self.convert_button.configure(state='disabled');self.stop_button.configure(state='normal')
        self.worker=threading.Thread(target=self._worker,args=(source,target,module,images),daemon=True);self.worker.start()

    def _worker(self,source,target,module,images):
        converted=skipped=failed=0;total=len(images)
        options={'dds_format':self.dds_format.get()}
        for index,path in enumerate(images,1):
            if self.stop_event.is_set():break
            relative=path.relative_to(source);folder=target/relative.parent if self.preserve_structure.get() else target;output=folder/(path.stem+'.dds')
            try:
                folder.mkdir(parents=True,exist_ok=True)
                if output.exists() and not self.overwrite.get():status='Skipped (exists)';skipped+=1
                else:module.convert_file(str(path),str(output),options);status='Converted';converted+=1
            except Exception as error:status=f'Error: {error}';failed+=1
            percent=index/total*100
            self.parent.after(0,lambda s=str(path),o=str(output),st=status,p=percent:self._row(s,o,st,p))
        self.parent.after(0,lambda:self._finish(converted,skipped,failed,self.stop_event.is_set()))

    def _row(self,source,output,status,percent):
        self.tree.insert('','end',values=(source,output,status));self.progress.set(percent);self.progress_text.set(f'{percent:.0f}%');self.status.set(status)
    def _finish(self,converted,skipped,failed,stopped):
        self.convert_button.configure(state='normal');self.stop_button.configure(state='disabled')
        self.status.set(f'{"Stopped" if stopped else "Complete"}: {converted} converted, {skipped} skipped, {failed} failed.')
    def stop(self):self.stop_event.set();self.stop_button.configure(state='disabled');self.status.set('Stopping after the current image…')


def build_converter_tool(parent):return ConverterTool(parent)
