"""Embedded PS1/PS2 asset extraction framework for AI Generator."""
import bz2, gzip, io, lzma, os, re, struct, subprocess, tempfile, threading, tkinter as tk, zipfile, zlib
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

# PS1 families observed in the supplied Parasite Eve utilities and PSXPrev.
# These are native signature scanners; AI Generator never launches the EXEs.
PS1_SIGNATURES=(
    ('Texture','PlayStation TIM',b'\x10\x00\x00\x00','.tim'),
    ('Model','PlayStation TMD',b'\x41\x00\x00\x00','.tmd'),
    ('Model','HMD',b'HMD','.hmd'),('Model','BFF',b'BFF','.bff'),
    ('Model','PMD',b'PMD','.pmd'),('Model','MOD / Croc',b'MOD','.mod'),
    ('Model','PSX model',b'PSX','.psx'),
    ('Animation','TOD',b'TOD','.tod'),('Animation','VDF',b'VDF','.vdf'),
    ('Animation','AN',b'AN\x00','.an'),
    ('Sound','PlayStation VAG',b'VAGp','.vag'),
    ('Sound','PlayStation VAB header',b'pBAV','.vh'),
    ('Sound','PlayStation SEQ',b'pQES','.seq'),
    ('Sound','CD-XA RIFF',b'CDXA','.xa'),
    ('Archive','Parasite Eve CDF reference',b'.cdf','.cdf'),
    ('Archive','Parasite Eve PKG reference',b'.pkg','.pkg'),
)

PS3_SIGNATURES=(
    ('Model','Twisted Metal C3D geometry',b'C3D','.vram'),
    ('Model','Twisted Metal geometry branch',b'Geometry','.vram'),
)

VITA_SIGNATURES=(
    ('Model','PSASBR MODL v8',b'MODL\x00\x00\x00\x08','.cmdl'),
    ('Texture','Vita GXT texture',b'GXT\x00','.ctxr'),
    ('Animation','PSASBR CESM animation',b'CESM','.cesm'),
)

@dataclass
class Asset:
    category:str;kind:str;offset:int;end:int;extension:str;name:str=''

class ExtractTool:
    def __init__(self,parent):
        self.parent=parent;self.stop_event=threading.Event();self.data=b'';self.path='';self.assets=[];self.worker=None
        self.profile=tk.StringVar(value='Auto Detect');self.status=tk.StringVar(value='Choose a section and input file.');self.progress=tk.DoubleVar()
        self.paths={};self.outputs={};self.trees={};self.assets_by_key={};self.index_files={};self.index_labels={};self.preview_canvases={};self.preview_images={};self.preview_photos={};self.preview_zoom={};self.model_viewers={};self.appended_files=[];self._build()
    def _build(self):
        self.parent.grid_columnconfigure(0,weight=1);self.parent.grid_rowconfigure(1,weight=1)
        header=ttk.Frame(self.parent,padding=(8,6));header.grid(row=0,column=0,sticky='ew');ttk.Label(header,text='Console / game profile').pack(side='left');ttk.Combobox(header,textvariable=self.profile,values=('Auto Detect','PS1 Generic','PSXPrev Compatible','Parasite Eve','Parasite Eve 2','PS2 Generic','Speed Racer PS2 / NIF','Wild Arms 3','Wild Arms Alter Code: F','PS3 Generic','Twisted Metal 2012','PSP / Vita Generic','PlayStation All-Stars Vita'),state='readonly',width=27).pack(side='left',padx=7);ttk.Label(header,text='Non-destructive: source files are never modified and helper EXEs are not launched.').pack(side='left',padx=8)
        self.tabs=ttk.Notebook(self.parent,style='Modern.TNotebook');self.tabs.grid(row=1,column=0,sticky='nsew',padx=7)
        for key,title in (('archives','Archives'),('models','Models'),('textures','Textures'),('animations','Animations'),('sound','Sound'),('blender','Blender'),('batch','Batch Processing')):
            page=ttk.Frame(self.tabs,padding=7);self.tabs.add(page,text=f'  {title}  ')
            if key=='batch':self._build_batch(page)
            elif key=='sound':
                try:
                    from sound_scanner import build_sound_scanner
                    sound_tabs=ttk.Notebook(page,style='Modern.TNotebook');sound_tabs.pack(fill='both',expand=True);scan_page=ttk.Frame(sound_tabs);convert_page=ttk.Frame(sound_tabs);sound_tabs.add(scan_page,text='  Scan / Playback  ');sound_tabs.add(convert_page,text='  Convert  ');self.sound_scanner=build_sound_scanner(scan_page);self.sound_scanner.build_convert_tab(convert_page)
                except Exception as error:ttk.Label(page,text=f'Sound scanner could not start: {error}').pack(anchor='w',padx=8,pady=8)
            elif key=='blender':
                try:
                    from blender_script_tool import build_blender_script_tool
                    self.blender_scripts=build_blender_script_tool(page)
                except Exception as error:ttk.Label(page,text=f'Blender scripts could not start: {error}').pack(anchor='w',padx=8,pady=8)
            else:self._build_section(page,key,title)
        footer=ttk.Frame(self.parent,padding=(8,4,8,7));footer.grid(row=2,column=0,sticky='ew');footer.columnconfigure(0,weight=1);ttk.Progressbar(footer,variable=self.progress,maximum=100,style='Accent.Horizontal.TProgressbar').grid(row=0,column=0,sticky='ew');self.stop_button=ttk.Button(footer,text='Stop',command=self.stop,state='disabled');self.stop_button.grid(row=0,column=1,padx=(7,0));ttk.Label(footer,textvariable=self.status).grid(row=1,column=0,columnspan=2,sticky='w',pady=(3,0))
    def _build_section(self,page,key,title):
        page.grid_columnconfigure(0,weight=1);page.grid_rowconfigure(2,weight=1);self.paths[key]=tk.StringVar();self.outputs[key]=tk.StringVar();self.index_files[key]=[];self.preview_zoom[key]=1.0
        source=ttk.Frame(page);source.grid(row=0,column=0,sticky='ew');source.columnconfigure(0,weight=1);ttk.Entry(source,textvariable=self.paths[key]).grid(row=0,column=0,sticky='ew');ttk.Button(source,text='Input file',command=lambda k=key:self.pick_file(k)).grid(row=0,column=1,padx=5);ttk.Button(source,text='Add Index File',command=lambda k=key:self.add_index_file(k)).grid(row=0,column=2);self.index_labels[key]=tk.StringVar(value='Index: 0');ttk.Label(source,textvariable=self.index_labels[key],width=10).grid(row=0,column=3,padx=5);ttk.Entry(source,textvariable=self.outputs[key],width=24).grid(row=0,column=4);ttk.Button(source,text='Output folder',command=lambda k=key:self.pick_output(k)).grid(row=0,column=5,padx=(5,0))
        actions=ttk.Frame(page);actions.grid(row=1,column=0,sticky='ew',pady=6)
        label={'archives':'Scan BIN / Archive','models':'Scan Mesh + Skeleton','textures':'Scan Texture Data','animations':'Scan Animation Data'}[key]
        ttk.Button(actions,text=label,command=lambda k=key:self.start_scan(k)).pack(side='left')
        if key=='archives':ttk.Button(actions,text='Decompress',command=self.open_decompressor).pack(side='left',padx=5)
        if key=='models':
            ttk.Button(actions,text='Import Skeleton',command=lambda:self.append_model_file('Skeleton')).pack(side='left',padx=5)
            ttk.Button(actions,text='Append Animation',command=lambda:self.append_model_file('Animation')).pack(side='left')
        ttk.Button(actions,text='Extract Selected',command=lambda k=key:self.extract_selected(k)).pack(side='right');ttk.Button(actions,text='Extract All',command=lambda k=key:self.extract_all(k)).pack(side='right',padx=5)
        pane=ttk.Panedwindow(page,orient='horizontal');pane.grid(row=2,column=0,sticky='nsew');listing=ttk.Frame(pane);preview=ttk.Frame(pane);pane.add(listing,weight=3);pane.add(preview,weight=2);listing.grid_rowconfigure(0,weight=1);listing.grid_columnconfigure(0,weight=1)
        tree=ttk.Treeview(listing,columns=('item','type','offset','size','output'),show='headings');self.trees[key]=tree
        for column,text,width in (('item','#',45),('type','Detected data',190),('offset','Offset',110),('size','Assumed size',110),('output','Output name',320)):tree.heading(column,text=text);tree.column(column,width=width,anchor='w')
        sy=ttk.Scrollbar(listing,orient='vertical',command=tree.yview);sx=ttk.Scrollbar(listing,orient='horizontal',command=tree.xview);tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);tree.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew');tree.bind('<<TreeviewSelect>>',lambda _e,k=key:self.preview_selected(k))
        if key in ('models','animations'):
            from extract_preview3d import ExtractPreview3D
            viewer=ExtractPreview3D(preview,lambda message:self.status.set(message));self.model_viewers[key]=viewer;self.preview_canvases[key]=viewer.canvas
            if key=='animations':viewer.enable_animation_controls(self.test_animation)
        else:
            pbar=ttk.Frame(preview);pbar.pack(fill='x');ttk.Label(pbar,text=f'{title} preview').pack(side='left');ttk.Button(pbar,text='Fit',command=lambda k=key:self.preview_fit(k)).pack(side='right')
            canvas=tk.Canvas(preview,bg='#020617',highlightthickness=1,highlightbackground='#334155');canvas.pack(fill='both',expand=True,pady=(4,0));canvas.create_text(20,20,text='Select an item to preview',anchor='nw',fill='#cbd5e1',tags='message');canvas.bind('<MouseWheel>',lambda e,k=key:self.preview_wheel(k,e));canvas.bind('<Configure>',lambda _e,k=key:self.draw_preview(k));self.preview_canvases[key]=canvas
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
    def add_index_file(self,key):
        paths=filedialog.askopenfilenames(title='Add filename/index companion files',filetypes=[('All files','*.*')])
        for path in paths:
            if path not in self.index_files[key]:self.index_files[key].append(path)
        self.index_labels[key].set(f'Index: {len(self.index_files[key])}')
        if paths:self.status.set(f'Added {len(paths)} index file(s). Stored names will be matched during the next scan.')
    def append_model_file(self,role):
        if len(self.appended_files)>=2:messagebox.showwarning('Model preview','Two companion files are already appended. Clear by reopening the tool.');return
        expected='Skeleton' if not self.appended_files else 'Animation'
        if role!=expected:messagebox.showwarning('Model preview',f'Append the {expected.lower()} file next.');return
        path=filedialog.askopenfilename(title=f'Import {role} file',filetypes=[('All files','*.*')])
        if path:
            self.appended_files.append((role,path));self.status.set(f'Appended {role.lower()}: {os.path.basename(path)} ({len(self.appended_files)}/2).')
            self.preview_selected('models')
    def _stored_names(self,key):
        wanted={'models':r'\.(?:fbx|obj|smd|dae|nif|dff|mesh|mdl|bin|dat)',
                'textures':r'\.(?:png|jpg|jpeg|dds|tga|bmp|tm2|tex|bin|dat)',
                'animations':r'\.(?:anm|anim|mot|smd|psa|cast|bin|dat)',
                'archives':r'\.(?:bin|dat|pak|arc|zip)'}[key]
        names=[]
        for path in self.index_files.get(key,[]):
            try:data=open(path,'rb').read()
            except Exception:continue
            for raw in re.findall(rb'[A-Za-z0-9_./\\ -]{2,180}',data):
                text=raw.decode('utf-8','ignore').strip().replace('\\','/')
                if re.search(wanted,text,re.I) and text not in names:names.append(os.path.basename(text))
        return names
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
        self.path=path;self.assets=[];self.assets_by_key[key]=[];self.trees[key].delete(*self.trees[key].get_children());self.stop_event.clear();self._running(True,f'Scanning {os.path.basename(path)}…');self.worker=threading.Thread(target=self._scan_worker,args=(key,),daemon=True);self.worker.start()
    def _scan_worker(self,key):
        category={'models':'Model','textures':'Texture','animations':'Animation'}.get(key);hits=[]
        profile=self.profile.get();use_ps1=profile in ('Auto Detect','PS1 Generic','PSXPrev Compatible','Parasite Eve','Parasite Eve 2');use_ps2=profile in ('Auto Detect','PS2 Generic','Speed Racer PS2 / NIF','Wild Arms 3','Wild Arms Alter Code: F');use_ps3=profile in ('Auto Detect','PS3 Generic','Twisted Metal 2012');use_vita=profile in ('Auto Detect','PSP / Vita Generic','PlayStation All-Stars Vita')
        signatures=[]
        if use_ps1:signatures.extend(PS1_SIGNATURES)
        if use_ps2:signatures.extend(PS2_SIGNATURES)
        if use_ps3:signatures.extend(PS3_SIGNATURES)
        if use_vita:signatures.extend(VITA_SIGNATURES)
        signatures=[entry for entry in signatures if not category or entry[0]==category]
        for signature_index,(group,kind,magic,extension) in enumerate(signatures):
            position=0
            while not self.stop_event.is_set():
                position=self.data.find(magic,position)
                if position<0:break
                if self._valid_signature(kind,position):hits.append((position,group,kind,extension))
                position+=max(1,len(magic))
            self.parent.after(0,lambda value=(signature_index+1)/max(1,len(signatures))*75:self.progress.set(value))
        hits.extend(self._profile_whole_file_hits(key,profile))
        if key=='archives':hits.extend(self._offset_table_hits())
        if use_ps1 and key=='archives':hits.extend(self._ps1_sector_hits(hits))
        # Auto Detect can find the same payload through both console tables.
        # Keep one candidate for each offset/category instead of creating a
        # one-byte duplicate asset.
        unique={}
        for hit in sorted(set(hits)):unique.setdefault((hit[0],hit[1]),hit)
        hits=sorted(unique.values());assets=[]
        stored_names=self._stored_names(key)
        for index,(offset,group,kind,extension) in enumerate(hits):
            end=hits[index+1][0] if index+1<len(hits) else len(self.data)
            if kind=='TIM2' and offset+16<=len(self.data):
                # TIM2 total size is frequently stored in the first picture header.
                try:end=min(end,offset+16+struct.unpack_from('<I',self.data,offset+16)[0])
                except Exception:pass
            elif kind=='PlayStation TIM' and offset+12<=len(self.data):
                # PS1 TIM stores one length-prefixed CLUT block when flag bit 3
                # is set, followed by one length-prefixed pixel block.
                try:
                    flags=struct.unpack_from('<I',self.data,offset+4)[0];cursor=offset+8
                    if flags&8:cursor+=struct.unpack_from('<I',self.data,cursor)[0]
                    cursor+=struct.unpack_from('<I',self.data,cursor)[0]
                    if offset<cursor<=len(self.data):end=min(end,cursor)
                except Exception:pass
            if kind=='Offset-table entry':extension=self._extension_from_header(self.data[offset:offset+32])
            name=stored_names[index] if index<len(stored_names) else f'{group.lower()}_{index+1:04d}_{offset:08X}{extension}';assets.append(Asset(group,kind,offset,max(offset+1,end),extension,name))
        self.parent.after(0,lambda:self._finish_scan(key,assets,self.stop_event.is_set()))
    def _profile_whole_file_hits(self,key,profile):
        """Recognize proprietary console assets by their selected whole-file extension."""
        extension=os.path.splitext(self.paths[key].get().strip())[1].lower();table={
            '.nif':('Model','Gamebryo NIF (whole file)','.nif'),
            '.vram':('Model','Twisted Metal 2012 VRAM geometry','.vram'),
            '.ascii':('Model','Twisted Metal ASCII geometry','.ascii'),
            '.cmdl':('Model','PSASBR Vita model','.cmdl'),
            '.cskn':('Model','PSASBR Vita skinned model','.cskn'),
            '.ctxr':('Texture','PSASBR Vita texture','.ctxr'),
            '.gxt':('Texture','Vita GXT texture','.gxt'),
            '.cesm':('Animation','PSASBR Vita animation','.cesm'),
            '.cdf':('Archive','Parasite Eve CDF archive','.cdf'),
            '.pkg':('Archive','PlayStation package archive','.pkg'),
        }
        entry=table.get(extension)
        if not entry:return []
        wanted={'models':'Model','textures':'Texture','animations':'Animation','archives':'Archive'}.get(key)
        if wanted and entry[0]!=wanted:return []
        return [(0,entry[0],entry[1],entry[2])]
    def _valid_signature(self,kind,offset):
        """Reject the most common false positives in raw PS1 scans."""
        try:
            if kind=='PlayStation TIM':
                flags=struct.unpack_from('<I',self.data,offset+4)[0]
                return (flags&~0x0F)==0 and (flags&7)<=3
            if kind=='PlayStation TMD':
                flags,count=struct.unpack_from('<II',self.data,offset+4)
                return flags in (0,1) and 0<count<65536
        except Exception:return False
        return True
    def _ps1_sector_hits(self,hits):
        """Add PS1 CD-sector aligned copies of recognized candidates.

        PSXPrev's BIN mode checks both 2048-byte data sectors and raw 2352-byte
        disc sectors. We annotate those boundaries without treating every sector
        as an asset.
        """
        existing={entry[0] for entry in hits};result=[]
        for sector in (2048,2352):
            for offset in existing:
                if offset and offset%sector==0:result.append((offset,'Archive',f'PS1 {sector}-byte sector boundary','.bin'))
        return result
    def _offset_table_hits(self):
        values=[]
        for offset in range(0,min(len(self.data)-4,0x10000),4):
            value=struct.unpack_from('<I',self.data,offset)[0]
            if value==0 and not values:continue
            if value%4 or value>=len(self.data) or (values and value<=values[-1]):break
            values.append(value)
        return [(value,'Archive','Offset-table entry','.dat') for value in values] if len(values)>=3 else []
    @staticmethod
    def _extension_from_header(data):
        signatures=((b'\x89PNG\r\n\x1a\n','.png'),(b'\xff\xd8\xff','.jpg'),(b'DDS ','.dds'),(b'RIFF','.wav'),(b'OggS','.ogg'),(b'fLaC','.flac'),(b'VAGp','.vag'),(b'PK\x03\x04','.zip'),(b'7z\xbc\xaf\x27\x1c','.7z'),(b'Rar!','.rar'),(b'\x1f\x8b','.gz'),(b'BZh','.bz2'),(b'\xfd7zXZ\x00','.xz'),(b'TIM2','.tm2'),(b'Gamebryo File Format','.nif'),(b'MODL','.cmdl'))
        for magic,extension in signatures:
            if data.startswith(magic):return extension
        if data.startswith(b'\x10\x00\x00\x00'):return '.tim'
        if data.startswith(b'\x41\x00\x00\x00'):return '.tmd'
        return '.dat'

    def open_decompressor(self):
        path=self.paths['archives'].get().strip();output=self.outputs['archives'].get().strip()
        if not os.path.isfile(path) or not output:messagebox.showwarning('Decompress','Choose an archive and output folder first.');return
        window=tk.Toplevel(self.parent);window.title('Overall Decompress');window.geometry('880x520');window.configure(bg='#111827');window.transient(self.parent.winfo_toplevel())
        frame=ttk.Frame(window,padding=10);frame.pack(fill='both',expand=True);frame.columnconfigure(1,weight=1);frame.rowconfigure(5,weight=1)
        engine=tk.StringVar(value='Auto / Native');quickbms=tk.StringVar(value=os.path.join(os.path.dirname(os.path.abspath(__file__)),'tools','quickbms.exe'));offzip=tk.StringVar(value=os.path.join(os.path.dirname(os.path.abspath(__file__)),'tools','offzip.exe'));script=tk.StringVar()
        ttk.Label(frame,text='Engine').grid(row=0,column=0,sticky='w');ttk.Combobox(frame,textvariable=engine,values=('Auto / Native','QuickBMS','Offzip (zlib)'),state='readonly').grid(row=0,column=1,sticky='ew')
        def executable_row(row,label,var):
            ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',pady=4);ttk.Entry(frame,textvariable=var).grid(row=row,column=1,sticky='ew',padx=5);ttk.Button(frame,text='Browse',command=lambda:file_pick(var)).grid(row=row,column=2)
        def file_pick(var):
            selected=filedialog.askopenfilename(filetypes=[('Executable','*.exe'),('All files','*.*')])
            if selected:var.set(selected)
        executable_row(1,'QuickBMS executable',quickbms);executable_row(2,'Offzip executable',offzip)
        archive_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','BMS.zip');members=[]
        try:
            with zipfile.ZipFile(archive_path) as archive:members=[name for name in archive.namelist() if name.lower().endswith('.bms') and not name.endswith('/')]
        except Exception:pass
        ttk.Label(frame,text='QuickBMS game/script').grid(row=3,column=0,sticky='w');combo=ttk.Combobox(frame,textvariable=script,values=members,state='readonly');combo.grid(row=3,column=1,columnspan=2,sticky='ew',pady=4)
        if members:script.set(members[0])
        ttk.Label(frame,text=f'{len(members):,} scripts indexed. Game names are taken from script filenames and searchable by typing the first letters.',wraplength=780).grid(row=4,column=0,columnspan=3,sticky='w')
        log=tk.Text(frame,bg='#020617',fg='#e2e8f0',insertbackground='white');log.grid(row=5,column=0,columnspan=3,sticky='nsew',pady=7)
        def run():
            os.makedirs(output,exist_ok=True);choice=engine.get();log.delete('1.0','end');log.insert('end',f'Input: {path}\nEngine: {choice}\n')
            def worker():
                try:
                    if choice=='QuickBMS':
                        if not os.path.isfile(quickbms.get()):raise FileNotFoundError('Choose a valid QuickBMS executable.')
                        if not script.get():raise RuntimeError('Choose a BMS game script.')
                        script_dir=os.path.join(tempfile.gettempdir(),'AI_Generator_BMS');os.makedirs(script_dir,exist_ok=True);script_path=os.path.join(script_dir,os.path.basename(script.get()))
                        with zipfile.ZipFile(archive_path) as archive:script_data=archive.read(script.get())
                        text=script_data.decode('utf-8','ignore')
                        if re.search(r'(?im)^\s*(?:execute|calldll|open\s+process|socket)\b',text):raise RuntimeError('This script requests external code/process/network features. Export and review it before running manually.')
                        with open(script_path,'wb') as target:target.write(script_data)
                        command=[quickbms.get(),script_path,path,output]
                    elif choice=='Offzip (zlib)':
                        if not os.path.isfile(offzip.get()):raise FileNotFoundError('Choose a valid Offzip executable.')
                        command=[offzip.get(),'-a',path,output,'0']
                    else:
                        command=None;data=open(path,'rb').read();name=os.path.splitext(os.path.basename(path))[0]+'_decompressed.dat'
                        if data.startswith(b'\x1f\x8b'):result=gzip.decompress(data)
                        elif data.startswith(b'BZh'):result=bz2.decompress(data)
                        elif data.startswith(b'\xfd7zXZ\x00'):result=lzma.decompress(data)
                        elif data[:2] in (b'\x78\x01',b'\x78\x5e',b'\x78\x9c',b'\x78\xda'):result=zlib.decompress(data)
                        else:result=self.lzss_decompress(data)
                        target=self.unique_path(output,name);open(target,'wb').write(result);message=f'Wrote {target} ({len(result):,} bytes)'
                    if command:
                        completed=subprocess.run(command,capture_output=True,text=True,timeout=3600)
                        message=(completed.stdout+'\n'+completed.stderr).strip()
                        if completed.returncode:raise RuntimeError(message or f'Engine returned {completed.returncode}')
                except Exception as error:message=f'ERROR: {error}'
                window.after(0,lambda:log.insert('end','\n'+message+'\n'))
            threading.Thread(target=worker,daemon=True).start()
        ttk.Button(frame,text='Decompress',command=run).grid(row=6,column=2,sticky='e')
    def _finish_scan(self,key,assets,stopped):
        self.assets=assets;self.assets_by_key[key]=assets;tree=self.trees[key]
        for index,item in enumerate(assets):tree.insert('','end',iid=str(index),values=(index+1,f'{item.category}: {item.kind}',f'0x{item.offset:08X}',self._size(item.end-item.offset),item.name))
        self.progress.set(100 if not stopped else self.progress.get());self._running(False,f'{"Stopped" if stopped else "Scan complete"}: {len(assets):,} candidate asset(s).')
        if assets:tree.selection_set('0');self.preview_selected(key)
    def _asset_payload(self,key,item):
        path=self.paths[key].get().strip()
        try:
            with open(path,'rb') as source:data=source.read()
            return data[item.offset:item.end]
        except Exception:return b''
    @staticmethod
    def _compression_name(payload):
        for magic,name in ((b'\x1f\x8b','GZIP'),(b'BZh','BZIP2'),(b'\xfd7zXZ\x00','LZMA/XZ'),(b'\x78\x9c','ZLIB'),(b'\x78\xda','ZLIB'),(b'Yaz0','Yaz0'),(b'\x04\x22\x4d\x18','LZ4')):
            if payload.startswith(magic):return name
        return ''
    def preview_selected(self,key):
        selection=self.trees[key].selection();assets=self.assets_by_key.get(key,[])
        if not selection or int(selection[0])>=len(assets):return
        item=assets[int(selection[0])];payload=self._asset_payload(key,item);canvas=self.preview_canvases[key];canvas.delete('all');self.preview_images.pop(key,None);self.preview_photos.pop(key,None)
        compressed=self._compression_name(payload)
        if compressed:
            canvas.create_text(canvas.winfo_width()/2,canvas.winfo_height()/2,text=f'PREVIEW ERROR\n{compressed} compressed data\nDecompress this block before previewing.',fill='#f87171',font=('Segoe UI Semibold',13),justify='center',tags='message');return
        if key=='textures':
            try:
                from PIL import Image
                with Image.open(io.BytesIO(payload)) as source:source.load();self.preview_images[key]=source.convert('RGBA')
                self.preview_zoom[key]=1.0;self.preview_fit(key);return
            except Exception as error:
                canvas.create_text(canvas.winfo_width()/2,canvas.winfo_height()/2,text=f'2D TEXTURE PREVIEW ERROR\n{item.kind}: {error}\nRaw/TIM2 data may require format settings or decompression.',fill='#f87171',justify='center',tags='message');return
        if key=='models':
            if not self.model_viewers[key].load_payload(payload):canvas.create_text(canvas.winfo_width()/2,canvas.winfo_height()/2,text='3D PREVIEW ERROR\nNo supported OBJ data or plausible vertex stream was found.',fill='#f87171',justify='center');return
            self.status.set(f'3D preview loaded: {item.name}. Drag to rotate, wheel to zoom, middle-drag to move.');return
        if key=='animations':
            model=self.model_viewers.get('models');viewer=self.model_viewers[key]
            if model and model.vertices:viewer.set_geometry(model.vertices,model.faces)
            viewer.animation_payload=payload;viewer.draw();self.status.set(f'Animation candidate loaded: {item.name}. Press Test Animation to validate it.');return
        companions='\n'.join(f'{role}: {os.path.basename(path)}' for role,path in self.appended_files) if key=='models' else ''
        canvas.create_text(20,20,anchor='nw',fill='#e2e8f0',font=('Consolas',10),text=f'{item.category}: {item.kind}\nName: {item.name}\nOffset: 0x{item.offset:08X}\nSize: {self._size(len(payload))}\n{companions}',tags='message')
    def test_animation(self):
        viewer=self.model_viewers.get('animations');payload=getattr(viewer,'animation_payload',b'') if viewer else b''
        if not viewer or not payload:messagebox.showerror('Animation Test','Select an animation result first.');return
        passed,message=viewer.test_animation(payload);self.status.set(message)
        if not passed:messagebox.showerror('Animation Test',message)
    def preview_fit(self,key):
        image=self.preview_images.get(key);canvas=self.preview_canvases.get(key)
        if image and canvas:self.preview_zoom[key]=min(max(1,canvas.winfo_width()-20)/image.width,max(1,canvas.winfo_height()-20)/image.height,8);self.draw_preview(key)
    def preview_wheel(self,key,event):
        if key=='textures' and self.preview_images.get(key):self.preview_zoom[key]=max(.05,min(32,self.preview_zoom[key]*(1.2 if event.delta>0 else 1/1.2)));self.draw_preview(key)
        return 'break'
    def draw_preview(self,key):
        image=self.preview_images.get(key);canvas=self.preview_canvases.get(key)
        if not image or not canvas:return
        from PIL import Image,ImageTk
        zoom=self.preview_zoom[key];size=(max(1,int(image.width*zoom)),max(1,int(image.height*zoom)));shown=image.resize(size,getattr(Image,'Resampling',Image).NEAREST if zoom>=2 else getattr(Image,'Resampling',Image).LANCZOS);photo=ImageTk.PhotoImage(shown);self.preview_photos[key]=photo;canvas.delete('all');canvas.create_image(canvas.winfo_width()/2,canvas.winfo_height()/2,image=photo)
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
        assets=self.assets_by_key.get(key,[]);self._write_assets(key,[assets[int(selection[0])]])
    def extract_all(self,key):self._write_assets(key,self.assets_by_key.get(key,[]))
    def _write_assets(self,key,assets):
        folder=self.outputs[key].get().strip()
        if not assets or not folder:messagebox.showwarning('Extract','Scan results and choose an output folder first.');return
        os.makedirs(folder,exist_ok=True)
        source_path=self.paths[key].get().strip();source_data=open(source_path,'rb').read()
        for item in assets:
            target=self.unique_path(folder,item.name)
            with open(target,'wb') as output:output.write(source_data[item.offset:item.end])
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
