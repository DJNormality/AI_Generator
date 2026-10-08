"""Binary research workspace with hex, strings, signatures, and safe extraction."""
import os, string, threading, tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk

SIGNATURES=(('PNG',b'\x89PNG\r\n\x1a\n'),('JPEG',b'\xff\xd8\xff'),('DDS',b'DDS '),('ZIP',b'PK\x03\x04'),('WAV',b'RIFF'),('OGG',b'OggS'),('PDF',b'%PDF-'),('GIF87',b'GIF87a'),('GIF89',b'GIF89a'),('BMP',b'BM'),('KTX',b'\xabKTX'),('GZIP',b'\x1f\x8b'),('7Z',b"7z\xbc\xaf\x27\x1c"))
DETECTED_EXTENSIONS={'PNG':'.png','JPEG':'.jpg','DDS':'.dds','ZIP':'.zip','WAV':'.wav','OGG':'.ogg','PDF':'.pdf','GIF87':'.gif','GIF89':'.gif','BMP':'.bmp','KTX':'.ktx','GZIP':'.gz','7Z':'.7z'}

def detected_extension(kind, payload, fallback='.file'):
    """Return a suffix verified from extracted bytes, then the scan result."""
    for signature_kind, magic in SIGNATURES:
        if payload.startswith(magic):
            return DETECTED_EXTENSIONS.get(signature_kind, fallback)
    normalized = str(kind or '').strip().upper()
    return DETECTED_EXTENSIONS.get(normalized, fallback)

@dataclass
class Embedded:
    kind:str;offset:int;end:int

class ResearchTool:
    def __init__(self,parent):
        self.parent=parent;self.data=b'';self.path='';self.search_results=[];self.embedded=[];self.stop_event=threading.Event();self.worker=None;self.header_open=True;self.page_offset=tk.IntVar(value=0);self.page_size=tk.IntVar(value=4096);self.query=tk.StringVar();self.mode=tk.StringVar(value='String');self.encoding=tk.StringVar(value='UTF-8');self.status=tk.StringVar(value='Open an input file.');self.base_name=tk.StringVar(value='TEST');self.output_ext=tk.StringVar(value='.file');self._build()
    def _build(self):
        self.parent.grid_columnconfigure(0,weight=1);self.parent.grid_rowconfigure(1,weight=1);self.header_shell=ttk.Frame(self.parent);self.header_shell.grid(row=0,column=0,sticky='ew');self.toggle_button=ttk.Button(self.header_shell,text='▼ Input file',command=self.toggle_header);self.toggle_button.pack(fill='x');self.header=ttk.Frame(self.header_shell,padding=6);self.header.pack(fill='x');self.header.columnconfigure(0,weight=1);self.path_var=tk.StringVar();ttk.Entry(self.header,textvariable=self.path_var).grid(row=0,column=0,sticky='ew');ttk.Button(self.header,text='Open file',command=self.open_file).grid(row=0,column=1,padx=5);ttk.Button(self.header,text='Detect embedded files',command=self.start_detect).grid(row=0,column=2);self.stop_button=ttk.Button(self.header,text='Stop scan',command=self.stop,state='disabled');self.stop_button.grid(row=0,column=3,padx=5)
        body=ttk.Panedwindow(self.parent,orient='horizontal');body.grid(row=1,column=0,sticky='nsew',padx=6,pady=5);left=ttk.Frame(body,padding=5);right=ttk.Frame(body,padding=5);body.add(left,weight=2);body.add(right,weight=1)
        nav=ttk.Frame(left);nav.pack(fill='x');ttk.Button(nav,text='Previous',command=lambda:self.change_page(-1)).pack(side='left');ttk.Button(nav,text='Next',command=lambda:self.change_page(1)).pack(side='left',padx=3);ttk.Label(nav,text='Offset').pack(side='left',padx=(8,2));ttk.Entry(nav,textvariable=self.page_offset,width=12).pack(side='left');ttk.Label(nav,text='Bytes').pack(side='left',padx=(8,2));ttk.Combobox(nav,textvariable=self.page_size,values=(1024,2048,4096,8192,16384),state='readonly',width=8).pack(side='left');ttk.Button(nav,text='Go',command=self.render_hex).pack(side='left',padx=4)
        self.hex_text=tk.Text(left,bg='#020617',fg='#cbd5e1',insertbackground='white',font=('Consolas',9),wrap='none');sy=ttk.Scrollbar(left,orient='vertical',command=self.hex_text.yview);sx=ttk.Scrollbar(left,orient='horizontal',command=self.hex_text.xview);self.hex_text.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);self.hex_text.pack(side='left',fill='both',expand=True,pady=(5,0));sy.pack(side='right',fill='y',pady=(5,0));sx.pack(side='bottom',fill='x')
        search=ttk.LabelFrame(right,text='Hex and string finder',padding=6);search.pack(fill='x');ttk.Combobox(search,textvariable=self.mode,values=('String','Hexadecimal'),state='readonly',width=13).grid(row=0,column=0);ttk.Entry(search,textvariable=self.query).grid(row=0,column=1,sticky='ew',padx=4);ttk.Combobox(search,textvariable=self.encoding,values=('ASCII','UTF-8','UTF-16LE'),state='readonly',width=10).grid(row=0,column=2);self.search_button=ttk.Button(search,text='Search',command=self.start_search);self.search_button.grid(row=0,column=3);search.columnconfigure(1,weight=1)
        notebook=ttk.Notebook(right);notebook.pack(fill='both',expand=True,pady=6);search_tab=ttk.Frame(notebook);files_tab=ttk.Frame(notebook);notebook.add(search_tab,text='Search results');notebook.add(files_tab,text='Embedded files')
        self.search_tree=ttk.Treeview(search_tab,columns=('number','offset','hex','preview'),show='headings');
        for key,title,width in (('number','#',45),('offset','Offset',100),('hex','Hex offset',105),('preview','Preview',260)):self.search_tree.heading(key,text=title);self.search_tree.column(key,width=width,anchor='w')
        sbar=ttk.Scrollbar(search_tab,orient='vertical',command=self.search_tree.yview);self.search_tree.configure(yscrollcommand=sbar.set);self.search_tree.pack(side='left',fill='both',expand=True);sbar.pack(side='right',fill='y');self.search_tree.bind('<Double-1>',self.goto_search)
        self.file_tree=ttk.Treeview(files_tab,columns=('number','type','offset','size'),show='headings');
        for key,title,width in (('number','#',45),('type','Type',80),('offset','Offset',110),('size','Size',100)):self.file_tree.heading(key,text=title);self.file_tree.column(key,width=width,anchor='w')
        fbar=ttk.Scrollbar(files_tab,orient='vertical',command=self.file_tree.yview);self.file_tree.configure(yscrollcommand=fbar.set);self.file_tree.pack(side='left',fill='both',expand=True);fbar.pack(side='right',fill='y')
        extract=ttk.LabelFrame(right,text='Extraction',padding=6);extract.pack(fill='x');ttk.Label(extract,text='Base').grid(row=0,column=0);ttk.Entry(extract,textvariable=self.base_name,width=12).grid(row=0,column=1,padx=3);ttk.Label(extract,text='Unknown fallback').grid(row=0,column=2);ttk.Entry(extract,textvariable=self.output_ext,width=8).grid(row=0,column=3,padx=3);ttk.Label(extract,text='Detected results automatically use their real file extension.',wraplength=330).grid(row=1,column=0,columnspan=4,sticky='w',pady=(4,0));ttk.Button(extract,text='Extract file',command=self.extract_one).grid(row=2,column=0,columnspan=2,sticky='ew',pady=4);ttk.Button(extract,text='Extract all',command=self.extract_all).grid(row=2,column=2,columnspan=2,sticky='ew',pady=4)
        bottom=ttk.Frame(self.parent,padding=(7,0,7,6));bottom.grid(row=2,column=0,sticky='ew');bottom.columnconfigure(0,weight=1);self.progress=tk.DoubleVar();ttk.Progressbar(bottom,variable=self.progress,maximum=100,style='Accent.Horizontal.TProgressbar').grid(row=0,column=0,sticky='ew');ttk.Label(bottom,textvariable=self.status).grid(row=1,column=0,sticky='w',pady=(3,0))
    def toggle_header(self):
        self.header_open=not self.header_open
        if self.header_open:self.header.pack(fill='x');self.toggle_button.config(text='▼ Input file')
        else:self.header.pack_forget();self.toggle_button.config(text='▶ Input file')
    def open_file(self):
        path=filedialog.askopenfilename(filetypes=[('All files','*.*')])
        if not path:return
        try:
            with open(path,'rb') as source:self.data=source.read()
            self.path=path;self.path_var.set(path);self.page_offset.set(0);self.search_results=[];self.embedded=[];self.search_tree.delete(*self.search_tree.get_children());self.file_tree.delete(*self.file_tree.get_children());self.render_hex();self.status.set(f'Loaded {len(self.data):,} bytes from {os.path.basename(path)}.')
        except Exception as error:messagebox.showerror('Open file',str(error))
    def render_hex(self):
        if not self.data:return
        try:start=max(0,min(len(self.data),int(str(self.page_offset.get()),0)))
        except Exception:start=0
        count=max(256,int(self.page_size.get()));payload=self.data[start:start+count];lines=[]
        for row in range(0,len(payload),16):
            chunk=payload[row:row+16];hexes=' '.join(f'{b:02X}' for b in chunk);ascii_text=''.join(chr(b) if 32<=b<127 else '.' for b in chunk);lines.append(f'{start+row:08X}  {hexes:<47}  |{ascii_text}|')
        self.hex_text.config(state='normal');self.hex_text.delete('1.0','end');self.hex_text.insert('1.0','\n'.join(lines));self.hex_text.config(state='disabled');self.page_offset.set(start)
    def change_page(self,direction):self.page_offset.set(max(0,self.page_offset.get()+direction*self.page_size.get()));self.render_hex()
    def query_bytes(self):
        value=self.query.get()
        if self.mode.get()=='Hexadecimal':
            cleaned=''.join(value.split());return bytes.fromhex(cleaned)
        return value.encode({'ASCII':'ascii','UTF-8':'utf-8','UTF-16LE':'utf-16le'}[self.encoding.get()],errors='replace')
    def start_search(self):
        if not self.data:messagebox.showwarning('Research','Open a file first.');return
        try:needle=self.query_bytes()
        except Exception as error:messagebox.showerror('Search',f'Invalid search value: {error}');return
        if not needle:messagebox.showwarning('Search','Enter a string or hexadecimal value.');return
        self.search_results=[];self.search_tree.delete(*self.search_tree.get_children());self.stop_event.clear();self.set_running(True,'Searching…');self.worker=threading.Thread(target=self.search_worker,args=(needle,),daemon=True);self.worker.start()
    def search_worker(self,needle):
        results=[];position=0;length=max(1,len(self.data))
        while not self.stop_event.is_set():
            position=self.data.find(needle,position)
            if position<0:break
            results.append(position);position+=max(1,len(needle));
            if len(results)%100==0:self.parent.after(0,lambda p=position/length*100:self.progress.set(p))
        self.parent.after(0,lambda:self.finish_search(results,self.stop_event.is_set()))
    def finish_search(self,results,stopped):
        self.search_results=results
        for index,offset in enumerate(results,1):preview=self.data[offset:offset+48];text=''.join(chr(b) if chr(b) in string.printable and b>=32 else '.' for b in preview);self.search_tree.insert('','end',values=(index,f'{offset:,}',f'0x{offset:08X}',text))
        self.set_running(False,f'{"Stopped" if stopped else "Search complete"}: {len(results):,} matches.');self.progress.set(100 if not stopped else self.progress.get())
    def start_detect(self):
        if not self.data:messagebox.showwarning('Research','Open a file first.');return
        self.embedded=[];self.file_tree.delete(*self.file_tree.get_children());self.stop_event.clear();self.set_running(True,'Scanning embedded signatures…');self.worker=threading.Thread(target=self.detect_worker,daemon=True);self.worker.start()
    def detect_worker(self):
        hits=[]
        for sig_index,(kind,magic) in enumerate(SIGNATURES):
            position=0
            while not self.stop_event.is_set():
                position=self.data.find(magic,position)
                if position<0:break
                hits.append((position,kind));position+=len(magic)
            self.parent.after(0,lambda p=(sig_index+1)/len(SIGNATURES)*100:self.progress.set(p))
            if self.stop_event.is_set():break
        hits=sorted(set(hits));files=[]
        for index,(offset,kind) in enumerate(hits):
            end=hits[index+1][0] if index+1<len(hits) else len(self.data)
            if kind=='PNG':marker=self.data.find(b'IEND',offset+8);end=marker+8 if marker>=0 else end
            elif kind=='JPEG':marker=self.data.find(b'\xff\xd9',offset+3);end=marker+2 if marker>=0 else end
            elif kind=='WAV' and offset+8<=len(self.data):end=min(len(self.data),offset+8+int.from_bytes(self.data[offset+4:offset+8],'little'))
            files.append(Embedded(kind,offset,max(offset+1,end)))
        self.parent.after(0,lambda:self.finish_detect(files,self.stop_event.is_set()))
    def finish_detect(self,files,stopped):
        self.embedded=files
        for index,item in enumerate(files,1):self.file_tree.insert('','end',iid=str(index-1),values=(index,item.kind,f'0x{item.offset:08X}',f'{item.end-item.offset:,} B'))
        self.set_running(False,f'{"Stopped" if stopped else "Scan complete"}: {len(files):,} embedded candidates.');self.progress.set(100 if not stopped else self.progress.get())
    def set_running(self,running,text):self.search_button.config(state='disabled' if running else 'normal');self.stop_button.config(state='normal' if running else 'disabled');self.status.set(text)
    def stop(self):self.stop_event.set();self.stop_button.config(state='disabled');self.status.set('Stopping scan…')
    def goto_search(self,_e=None):
        selection=self.search_tree.selection()
        if selection:
            values=self.search_tree.item(selection[0],'values');self.page_offset.set(int(values[2],16));self.render_hex()
    @staticmethod
    def unique_name(folder,base,extension,reserved=None):
        reserved=reserved or set();extension=extension if extension.startswith('.') else '.'+extension;candidate=os.path.join(folder,base+extension);number=1
        while os.path.exists(candidate) or os.path.normcase(candidate) in reserved:candidate=os.path.join(folder,f'{base}_{number}{extension}');number+=1
        return candidate
    def selected_embedded(self):
        selection=self.file_tree.selection();return self.embedded[int(selection[0])] if selection else None
    def extract_one(self):
        item=self.selected_embedded()
        if not item:messagebox.showwarning('Extract','Select an embedded file first.');return
        folder=filedialog.askdirectory(title='Extract selected file');
        if not folder:return
        payload=self.data[item.offset:item.end]
        extension=detected_extension(item.kind,payload,self.output_ext.get().strip() or '.file')
        path=self.unique_name(folder,self.base_name.get().strip() or 'TEST',extension)
        with open(path,'wb') as output:output.write(payload)
        self.status.set(f'Extracted {os.path.basename(path)} as {extension}')
    def extract_all(self):
        if not self.embedded:messagebox.showwarning('Extract all','Detect embedded files first.');return
        folder=filedialog.askdirectory(title='Extract all files');
        if not folder:return
        reserved=set();base=self.base_name.get().strip() or 'TEST';fallback=self.output_ext.get().strip() or '.file'
        for item in self.embedded:
            payload=self.data[item.offset:item.end];extension=detected_extension(item.kind,payload,fallback)
            path=self.unique_name(folder,base,extension,reserved);reserved.add(os.path.normcase(path))
            with open(path,'wb') as output:output.write(payload)
        self.status.set(f'Extracted {len(self.embedded):,} files with verified detected extensions.')

def build_research_tool(parent):return ResearchTool(parent)
