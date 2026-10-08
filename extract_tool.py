"""Embedded PS2 asset extraction framework for AI Generator."""
import os, struct, threading, tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk


PS2_SIGNATURES=(
    ('Texture','TIM2',b'TIM2','.tm2'),('Sound','VAG',b'VAGp','.vag'),
    ('Sound','WAV',b'RIFF','.wav'),('Sound','Sony bank header',b'SShd','.sshd'),
    ('Sound','Sony bank body',b'SSbd','.ssbd'),('Model','Gamebryo NIF',b'Gamebryo File Format','.nif'),
    ('Model','RenderWare',b'\x10\x00\x00\x00','.dff'),('Animation','MOT',b'MOT\x00','.mot'),
    ('Animation','ANM',b'ANM\x00','.anm'),('Archive','ZIP',b'PK\x03\x04','.zip'),
    ('Image','PNG',b'\x89PNG\r\n\x1a\n','.png'),('Image','JPEG',b'\xff\xd8\xff','.jpg'),
)

@dataclass
class Asset:
    category:str;kind:str;offset:int;end:int;extension:str;name:str=''

class ExtractTool:
    def __init__(self,parent):
        self.parent=parent;self.stop_event=threading.Event();self.data=b'';self.path='';self.assets=[];self.worker=None
        self.profile=tk.StringVar(value='PS2 Generic');self.status=tk.StringVar(value='Choose a section and input file.');self.progress=tk.DoubleVar()
        self.paths={};self.outputs={};self.trees={};self._build()
    def _build(self):
        self.parent.grid_columnconfigure(0,weight=1);self.parent.grid_rowconfigure(1,weight=1)
        header=ttk.Frame(self.parent,padding=(8,6));header.grid(row=0,column=0,sticky='ew');ttk.Label(header,text='PS2 profile').pack(side='left');ttk.Combobox(header,textvariable=self.profile,values=('PS2 Generic','Wild Arms 3','Wild Arms Alter Code: F','Auto Detect'),state='readonly',width=24).pack(side='left',padx=7);ttk.Label(header,text='Extraction functions are non-destructive; source files are never modified.').pack(side='left',padx=8)
        self.tabs=ttk.Notebook(self.parent,style='Modern.TNotebook');self.tabs.grid(row=1,column=0,sticky='nsew',padx=7)
        for key,title in (('archives','Archives'),('models','Models'),('textures','Textures'),('animations','Animations'),('batch','Batch Processing')):
            page=ttk.Frame(self.tabs,padding=7);self.tabs.add(page,text=f'  {title}  ')
            if key=='batch':self._build_batch(page)
            else:self._build_section(page,key,title)
        footer=ttk.Frame(self.parent,padding=(8,4,8,7));footer.grid(row=2,column=0,sticky='ew');footer.columnconfigure(0,weight=1);ttk.Progressbar(footer,variable=self.progress,maximum=100,style='Accent.Horizontal.TProgressbar').grid(row=0,column=0,sticky='ew');self.stop_button=ttk.Button(footer,text='Stop',command=self.stop,state='disabled');self.stop_button.grid(row=0,column=1,padx=(7,0));ttk.Label(footer,textvariable=self.status).grid(row=1,column=0,columnspan=2,sticky='w',pady=(3,0))
    def _build_section(self,page,key,title):
        page.grid_columnconfigure(0,weight=1);page.grid_rowconfigure(2,weight=1);self.paths[key]=tk.StringVar();self.outputs[key]=tk.StringVar()
        source=ttk.Frame(page);source.grid(row=0,column=0,sticky='ew');source.columnconfigure(0,weight=1);ttk.Entry(source,textvariable=self.paths[key]).grid(row=0,column=0,sticky='ew');ttk.Button(source,text='Input file',command=lambda k=key:self.pick_file(k)).grid(row=0,column=1,padx=5);ttk.Entry(source,textvariable=self.outputs[key],width=30).grid(row=0,column=2);ttk.Button(source,text='Output folder',command=lambda k=key:self.pick_output(k)).grid(row=0,column=3,padx=(5,0))
        actions=ttk.Frame(page);actions.grid(row=1,column=0,sticky='ew',pady=6)
        label={'archives':'Scan BIN / Archive','models':'Scan Mesh + Skeleton','textures':'Scan Texture Data','animations':'Scan Animation Data'}[key]
        ttk.Button(actions,text=label,command=lambda k=key:self.start_scan(k)).pack(side='left')
        if key=='archives':ttk.Button(actions,text='LZSS Decompress',command=self.start_lzss).pack(side='left',padx=5)
        ttk.Button(actions,text='Extract Selected',command=lambda k=key:self.extract_selected(k)).pack(side='right');ttk.Button(actions,text='Extract All',command=lambda k=key:self.extract_all(k)).pack(side='right',padx=5)
        tree=ttk.Treeview(page,columns=('item','type','offset','size','output'),show='headings');self.trees[key]=tree
        for column,text,width in (('item','#',45),('type','Detected data',190),('offset','Offset',110),('size','Assumed size',110),('output','Output name',320)):tree.heading(column,text=text);tree.column(column,width=width,anchor='w')
        sy=ttk.Scrollbar(page,orient='vertical',command=tree.yview);sx=ttk.Scrollbar(page,orient='horizontal',command=tree.xview);tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);tree.grid(row=2,column=0,sticky='nsew');sy.grid(row=2,column=1,sticky='ns');sx.grid(row=3,column=0,sticky='ew')
    def _build_batch(self,page):
        page.grid_columnconfigure(1,weight=1);self.batch_input=tk.StringVar();self.batch_output=tk.StringVar();self.batch_lzss=tk.BooleanVar(value=True);self.batch_scan=tk.BooleanVar(value=True)
        for row,(label,var,command) in enumerate((('Input directory',self.batch_input,self.pick_batch_input),('Output directory',self.batch_output,self.pick_batch_output))):ttk.Label(page,text=label).grid(row=row,column=0,sticky='w',pady=5);ttk.Entry(page,textvariable=var).grid(row=row,column=1,sticky='ew',padx=7);ttk.Button(page,text='Browse',command=command).grid(row=row,column=2)
        ttk.Checkbutton(page,text='Attempt LZSS decompression',variable=self.batch_lzss).grid(row=2,column=1,sticky='w',pady=5);ttk.Checkbutton(page,text='Scan decompressed data for PS2 assets',variable=self.batch_scan).grid(row=3,column=1,sticky='w',pady=5);ttk.Button(page,text='Run Batch Processing',command=self.start_batch).grid(row=4,column=1,sticky='w',pady=10)
        self.batch_log=tk.Listbox(page,bg='#0f172a',fg='#e5e7eb',height=18);self.batch_log.grid(row=5,column=0,columnspan=3,sticky='nsew');page.grid_rowconfigure(5,weight=1)
    def pick_file(self,key):
        path=filedialog.askopenfilename(filetypes=[('All files','*.*')]);
        if path:self.paths[key].set(path);self.outputs[key].set(self.outputs[key].get() or os.path.join(os.path.dirname(path),os.path.splitext(os.path.basename(path))[0]+'_extracted'))
    def pick_output(self,key):
        path=filedialog.askdirectory();
        if path:self.outputs[key].set(path)
    def pick_batch_input(self):
        path=filedialog.askdirectory();
        if path:self.batch_input.set(path)
    def pick_batch_output(self):
        path=filedialog.askdirectory();
        if path:self.batch_output.set(path)
    def start_scan(self,key):
        path=self.paths[key].get().strip()
        if not os.path.isfile(path):messagebox.showwarning('Extract','Choose a valid input file.');return
        with open(path,'rb') as source:self.data=source.read()
        self.path=path;self.assets=[];self.trees[key].delete(*self.trees[key].get_children());self.stop_event.clear();self._running(True,f'Scanning {os.path.basename(path)}…');self.worker=threading.Thread(target=self._scan_worker,args=(key,),daemon=True);self.worker.start()
    def _scan_worker(self,key):
        category={'models':'Model','textures':'Texture','animations':'Animation'}.get(key);hits=[]
        signatures=[entry for entry in PS2_SIGNATURES if not category or entry[0]==category]
        for signature_index,(group,kind,magic,extension) in enumerate(signatures):
            position=0
            while not self.stop_event.is_set():
                position=self.data.find(magic,position)
                if position<0:break
                hits.append((position,group,kind,extension));position+=max(1,len(magic))
            self.parent.after(0,lambda value=(signature_index+1)/max(1,len(signatures))*75:self.progress.set(value))
        if key=='archives':hits.extend(self._offset_table_hits())
        hits=sorted(set(hits));assets=[]
        for index,(offset,group,kind,extension) in enumerate(hits):
            end=hits[index+1][0] if index+1<len(hits) else len(self.data)
            if kind=='TIM2' and offset+16<=len(self.data):
                # TIM2 total size is frequently stored in the first picture header.
                try:end=min(end,offset+16+struct.unpack_from('<I',self.data,offset+16)[0])
                except Exception:pass
            name=f'{group.lower()}_{index+1:04d}_{offset:08X}{extension}';assets.append(Asset(group,kind,offset,max(offset+1,end),extension,name))
        self.parent.after(0,lambda:self._finish_scan(key,assets,self.stop_event.is_set()))
    def _offset_table_hits(self):
        values=[]
        for offset in range(0,min(len(self.data)-4,0x10000),4):
            value=struct.unpack_from('<I',self.data,offset)[0]
            if value==0 and not values:continue
            if value%4 or value>=len(self.data) or (values and value<=values[-1]):break
            values.append(value)
        return [(value,'Archive','Offset-table entry','.bin') for value in values] if len(values)>=3 else []
    def _finish_scan(self,key,assets,stopped):
        self.assets=assets;tree=self.trees[key]
        for index,item in enumerate(assets):tree.insert('','end',iid=str(index),values=(index+1,f'{item.category}: {item.kind}',f'0x{item.offset:08X}',self._size(item.end-item.offset),item.name))
        self.progress.set(100 if not stopped else self.progress.get());self._running(False,f'{"Stopped" if stopped else "Scan complete"}: {len(assets):,} candidate asset(s).')
    def start_lzss(self):
        path=self.paths['archives'].get().strip();output=self.outputs['archives'].get().strip()
        if not os.path.isfile(path) or not output:messagebox.showwarning('LZSS','Choose an archive and output folder.');return
        self.stop_event.clear();self._running(True,'Trying PS2 LZSS decompression…')
        def worker():
            try:
                data=open(path,'rb').read();result=self.lzss_decompress(data);os.makedirs(output,exist_ok=True);target=self.unique_path(output,os.path.splitext(os.path.basename(path))[0]+'_decompressed.bin');open(target,'wb').write(result);message=f'LZSS output: {target} ({len(result):,} bytes)'
            except Exception as error:message=f'LZSS failed: {error}'
            self.parent.after(0,lambda:self._running(False,message))
        threading.Thread(target=worker,daemon=True).start()
    def lzss_decompress(self,data):
        # Okumura/PS2-style 4 KB ring buffer, LSB-first flag byte,
        # 12-bit distance and 4-bit length (+3). It intentionally rejects
        # implausible expansion instead of writing unbounded output.
        source=0;output=bytearray();window=bytearray(b' ' * 4096);write=4078
        while source<len(data) and not self.stop_event.is_set():
            flags=data[source];source+=1
            for bit in range(8):
                if source>=len(data):break
                if flags&(1<<bit):value=data[source];source+=1;output.append(value);window[write]=value;write=(write+1)&4095
                else:
                    if source+1>=len(data):source=len(data);break
                    lo,hi=data[source],data[source+1];source+=2;read=lo|((hi&0xF0)<<4);length=(hi&0x0F)+3
                    for _ in range(length):value=window[read];read=(read+1)&4095;output.append(value);window[write]=value;write=(write+1)&4095
                if len(output)>max(64*1024*1024,len(data)*128):raise ValueError('Rejected implausible LZSS expansion. Select the correct profile or source block.')
            if source%65536<9:self.parent.after(0,lambda value=source/max(1,len(data))*100:self.progress.set(value))
        if self.stop_event.is_set():raise RuntimeError('Stopped')
        if len(output)<=len(data):raise ValueError('The selected file does not appear to use the supported PS2 LZSS variant.')
        return bytes(output)
    def extract_selected(self,key):
        selection=self.trees[key].selection()
        if not selection:messagebox.showwarning('Extract','Select a result first.');return
        self._write_assets(key,[self.assets[int(selection[0])]])
    def extract_all(self,key):self._write_assets(key,self.assets)
    def _write_assets(self,key,assets):
        folder=self.outputs[key].get().strip()
        if not assets or not folder:messagebox.showwarning('Extract','Scan results and choose an output folder first.');return
        os.makedirs(folder,exist_ok=True)
        for item in assets:
            target=self.unique_path(folder,item.name)
            with open(target,'wb') as output:output.write(self.data[item.offset:item.end])
        self.status.set(f'Extracted {len(assets):,} item(s) without overwriting files.')
    def start_batch(self):
        source=self.batch_input.get().strip();output=self.batch_output.get().strip()
        if not os.path.isdir(source) or not output:messagebox.showwarning('Batch','Choose valid input and output directories.');return
        paths=[os.path.join(root,name) for root,_,names in os.walk(source) for name in names];self.batch_log.delete(0,'end');self.stop_event.clear();self._running(True,f'Batch processing {len(paths):,} files…')
        def worker():
            for index,path in enumerate(paths):
                if self.stop_event.is_set():break
                relative=os.path.relpath(path,source);folder=os.path.join(output,os.path.dirname(relative));os.makedirs(folder,exist_ok=True);message=f'{index+1}/{len(paths)} {relative}'
                try:
                    data=open(path,'rb').read()
                    if self.batch_lzss.get():
                        try:data=self.lzss_decompress(data);relative=os.path.splitext(relative)[0]+'_decompressed.bin'
                        except Exception:pass
                    target=self.unique_path(os.path.join(output,os.path.dirname(relative)),os.path.basename(relative));open(target,'wb').write(data)
                except Exception as error:message+=f' — {error}'
                self.parent.after(0,lambda m=message,v=(index+1)/max(1,len(paths))*100:(self.batch_log.insert('end',m),self.progress.set(v)))
            self.parent.after(0,lambda:self._running(False,'Batch stopped.' if self.stop_event.is_set() else 'Batch processing complete.'))
        threading.Thread(target=worker,daemon=True).start()
    def stop(self):self.stop_event.set();self.status.set('Stopping…');self.stop_button.config(state='disabled')
    def _running(self,running,message):self.stop_button.config(state='normal' if running else 'disabled');self.status.set(message)
    @staticmethod
    def unique_path(folder,name):
        os.makedirs(folder,exist_ok=True);path=os.path.join(folder,name);base,extension=os.path.splitext(path);number=1
        while os.path.exists(path):path=f'{base}_{number}{extension}';number+=1
        return path
    @staticmethod
    def _size(value):
        for unit in ('B','KB','MB','GB'):
            if value<1024 or unit=='GB':return f'{value:.1f} {unit}' if unit!='B' else f'{int(value)} B'
            value/=1024

def build_extract_tool(parent):return ExtractTool(parent)
