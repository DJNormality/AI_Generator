"""Raw sound-bank scanner and structure-preserving extractor for AI Generator."""
import os, struct, threading, tkinter as tk, zipfile
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk


SIGNATURES = (
    ('WAV / Wwise WEM', b'RIFF', '.wav'), ('AIFF', b'FORM', '.aiff'),
    ('Ogg Vorbis / Opus', b'OggS', '.ogg'), ('FLAC', b'fLaC', '.flac'),
    ('MP3 ID3', b'ID3', '.mp3'), ('MIDI', b'MThd', '.mid'),
    ('FSB4 bank', b'FSB4', '.fsb'), ('FSB5 bank', b'FSB5', '.fsb'),
    ('Wwise bank', b'BKHD', '.bnk'), ('PlayStation VAG', b'VAGp', '.vag'),
    ('PlayStation VAB header', b'pBAV', '.vh'),
    ('PlayStation SEQ', b'pQES', '.seq'), ('PlayStation CD-XA', b'CDXA', '.xa'),
    ('CRI ADX', b'\x80\x00', '.adx'), ('Nintendo BRSTM', b'RSTM', '.brstm'),
    ('Nintendo BFSTM', b'FSTM', '.bfstm'), ('Nintendo BCSTM', b'CSTM', '.bcstm'),
    ('Xbox XMA', b'XMA2', '.xma'), ('Tracker XM', b'Extended Module: ', '.xm'),
    ('Tracker S3M', b'SCRM', '.s3m'), ('Tracker IT', b'IMPM', '.it'),
    ('PlayStation PSF', b'PSF', '.psf'), ('AAC ADTS', b'\xff\xf1', '.aac'),
    ('AAC ADTS', b'\xff\xf9', '.aac'),
)

CODEC_GUIDE = (
    'PCM / IEEE Float, Microsoft ADPCM, IMA ADPCM, MP1/MP2/MP3, AAC/ADTS, '
    'Vorbis, Opus, FLAC, ATRAC/AT3, Xbox XMA, Nintendo DSP ADPCM, Sony VAG, '
    'CRI ADX/HCA, Wwise WEM/BNK, FMOD FSB4/FSB5, tracker and MIDI signatures'
)


@dataclass
class SoundItem:
    name: str
    kind: str
    offset: int
    end: int
    relative_path: str


class SoundScanner:
    def __init__(self, parent):
        self.parent=parent;self.data=b'';self.path='';self.items=[];self.stop_event=threading.Event();self.worker=None
        self.path_var=tk.StringVar();self.status=tk.StringVar(value='Open any file or sound bank to begin.');self.progress=tk.DoubleVar()
        self._build()

    def _build(self):
        self.parent.grid_columnconfigure(0,weight=1);self.parent.grid_rowconfigure(2,weight=1)
        top=ttk.Frame(self.parent,padding=8);top.grid(row=0,column=0,sticky='ew');top.columnconfigure(0,weight=1)
        ttk.Entry(top,textvariable=self.path_var).grid(row=0,column=0,sticky='ew');ttk.Button(top,text='Open input',command=self.open_file).grid(row=0,column=1,padx=5)
        self.scan_button=ttk.Button(top,text='Scan sound data',command=self.start_scan);self.scan_button.grid(row=0,column=2)
        self.stop_button=ttk.Button(top,text='Stop scan',command=self.stop,state='disabled');self.stop_button.grid(row=0,column=3,padx=(5,0))
        guide=ttk.LabelFrame(self.parent,text='Documented formats and codecs',padding=7);guide.grid(row=1,column=0,sticky='ew',padx=8);ttk.Label(guide,text=CODEC_GUIDE,wraplength=980,justify='left').pack(anchor='w')
        body=ttk.Frame(self.parent,padding=8);body.grid(row=2,column=0,sticky='nsew');body.grid_rowconfigure(0,weight=1);body.grid_columnconfigure(0,weight=1)
        self.tree=ttk.Treeview(body,columns=('item','type','offset','size','path'),show='headings')
        for key,title,width in (('item','Item',60),('type','Assumed format',180),('offset','Offset',110),('size','Size',110),('path','Saved structure',360)):
            self.tree.heading(key,text=title);self.tree.column(key,width=width,anchor='w')
        sy=ttk.Scrollbar(body,orient='vertical',command=self.tree.yview);sx=ttk.Scrollbar(body,orient='horizontal',command=self.tree.xview);self.tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);self.tree.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew')
        bottom=ttk.Frame(self.parent,padding=(8,0,8,8));bottom.grid(row=3,column=0,sticky='ew');bottom.columnconfigure(0,weight=1)
        ttk.Progressbar(bottom,variable=self.progress,maximum=100,style='Accent.Horizontal.TProgressbar').grid(row=0,column=0,sticky='ew')
        ttk.Button(bottom,text='Extract selected',command=self.extract_selected).grid(row=0,column=1,padx=(8,4));ttk.Button(bottom,text='Extract all',command=self.extract_all).grid(row=0,column=2)
        ttk.Label(bottom,textvariable=self.status).grid(row=1,column=0,columnspan=3,sticky='w',pady=(4,0))

    def open_file(self):
        path=filedialog.askopenfilename(filetypes=[('All files','*.*')])
        if not path:return
        try:
            with open(path,'rb') as source:self.data=source.read()
            self.path=path;self.path_var.set(path);self.items=[];self.tree.delete(*self.tree.get_children());self.progress.set(0);self.status.set(f'Loaded {len(self.data):,} bytes.')
        except Exception as error:messagebox.showerror('Sound scanner',str(error))

    def start_scan(self):
        if not self.data:messagebox.showwarning('Sound scanner','Open an input file first.');return
        self.stop_event.clear();self.items=[];self.tree.delete(*self.tree.get_children());self.progress.set(0);self.scan_button.config(state='disabled');self.stop_button.config(state='normal');self.status.set('Scanning documented sound signatures…');self.worker=threading.Thread(target=self._scan,daemon=True);self.worker.start()

    def _scan(self):
        hits=[]
        # Preserve real archive paths when a ZIP-compatible sound package is supplied.
        if zipfile.is_zipfile(self.path):
            try:
                with zipfile.ZipFile(self.path) as archive:
                    for info in archive.infolist():
                        if self.stop_event.is_set():break
                        ext=os.path.splitext(info.filename)[1].lower()
                        if ext in ('.wav','.mp3','.ogg','.opus','.flac','.aac','.aiff','.aif','.mid','.midi','.wem','.bnk','.fsb','.vag','.adx','.hca','.at3','.xma','.dsp','.brstm','.bfstm','.bcstm','.xm','.mod','.s3m','.it'):
                            hits.append(SoundItem(os.path.basename(info.filename),ext[1:].upper(),-1,info.file_size,info.filename))
            except Exception:pass
        total=max(1,len(SIGNATURES))
        raw=[]
        for sig_index,(kind,magic,extension) in enumerate(SIGNATURES):
            position=0
            while not self.stop_event.is_set():
                position=self.data.find(magic,position)
                if position<0:break
                # S3M's SCRM marker belongs 44 bytes into the file.
                start=max(0,position-44) if kind=='Tracker S3M' else position
                raw.append((start,kind,extension));position+=max(1,len(magic))
            self.parent.after(0,lambda value=(sig_index+1)/total*100:self.progress.set(value))
            if self.stop_event.is_set():break
        raw=sorted(set(raw))
        for index,(offset,kind,extension) in enumerate(raw):
            end=raw[index+1][0] if index+1<len(raw) else len(self.data)
            if self.data[offset:offset+4] in (b'RIFF',b'FORM') and offset+8<=len(self.data):end=min(len(self.data),offset+8+int.from_bytes(self.data[offset+4:offset+8],'little'))
            elif kind=='PlayStation VAG' and offset+48<=len(self.data):
                data_size=int.from_bytes(self.data[offset+12:offset+16],'big');end=min(end,offset+48+data_size)
            elif kind=='MIDI' and offset+14<=len(self.data):end=self._midi_end(offset,end)
            relative=os.path.join('sound_data',f'{index+1:04d}_{offset:08X}{extension}')
            hits.append(SoundItem(os.path.basename(relative),kind,offset,max(offset+1,end),relative))
        self.parent.after(0,lambda:self._finish(hits,self.stop_event.is_set()))

    def _midi_end(self,start,fallback):
        try:
            tracks=int.from_bytes(self.data[start+10:start+12],'big');position=start+14
            for _ in range(tracks):
                marker=self.data.find(b'MTrk',position,fallback)
                if marker<0:return fallback
                length=int.from_bytes(self.data[marker+4:marker+8],'big');position=marker+8+length
            return min(fallback,position)
        except Exception:return fallback

    def _finish(self,items,stopped):
        self.items=items
        for index,item in enumerate(items):
            size=item.end if item.offset<0 else item.end-item.offset;self.tree.insert('','end',iid=str(index),values=(index+1,item.kind,'Archive' if item.offset<0 else f'0x{item.offset:08X}',self._size(size),item.relative_path))
        self.scan_button.config(state='normal');self.stop_button.config(state='disabled');self.status.set(f'{"Stopped" if stopped else "Scan complete"}: {len(items):,} sound item(s).')

    @staticmethod
    def _size(value):
        for unit in ('B','KB','MB','GB'):
            if value<1024 or unit=='GB':return f'{value:.1f} {unit}' if unit!='B' else f'{int(value)} B'
            value/=1024

    def stop(self):self.stop_event.set();self.stop_button.config(state='disabled');self.status.set('Stopping scan…')
    def _safe_path(self,root,relative):
        relative=os.path.normpath(relative).lstrip('/\\')
        if relative.startswith('..'):relative=os.path.basename(relative)
        path=os.path.join(root,relative);os.makedirs(os.path.dirname(path),exist_ok=True);base,ext=os.path.splitext(path);number=1;candidate=path
        while os.path.exists(candidate):candidate=f'{base}_{number}{ext}';number+=1
        return candidate

    def _extract(self,item,folder):
        target=self._safe_path(folder,item.relative_path)
        if item.offset<0:
            with zipfile.ZipFile(self.path) as archive,archive.open(item.relative_path) as source,open(target,'wb') as output:output.write(source.read())
        else:
            with open(target,'wb') as output:output.write(self.data[item.offset:item.end])
        return target

    def extract_selected(self):
        selection=self.tree.selection()
        if not selection:messagebox.showwarning('Extract','Select a sound item first.');return
        folder=filedialog.askdirectory(title='Extract selected sound');
        if folder:self.status.set(f'Extracted {self._extract(self.items[int(selection[0])],folder)}')
    def extract_all(self):
        if not self.items:messagebox.showwarning('Extract all','Scan for sound data first.');return
        folder=filedialog.askdirectory(title='Extract all sounds');
        if not folder:return
        for item in self.items:self._extract(item,folder)
        self.status.set(f'Extracted {len(self.items):,} sound item(s) with folder structure preserved.')


def build_sound_scanner(parent):return SoundScanner(parent)
