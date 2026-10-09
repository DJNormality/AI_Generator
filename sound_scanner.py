"""Raw sound-bank scanner and structure-preserving extractor for AI Generator."""
import os, random, shutil, struct, tempfile, threading, tkinter as tk, zipfile
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
        self.current_index=0;self.repeat=tk.BooleanVar();self.shuffle=tk.BooleanVar();self.position=tk.DoubleVar();self.play_paused=False;self.temp_audio=[];self.current_duration=1.
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
        playback=ttk.Frame(self.parent,padding=(8,0,8,8));playback.grid(row=4,column=0,sticky='ew');playback.columnconfigure(4,weight=1);ttk.Button(playback,text='Previous',command=lambda:self.move_track(-1)).grid(row=0,column=0);ttk.Button(playback,text='Play',command=self.play_selected).grid(row=0,column=1,padx=3);ttk.Button(playback,text='Pause',command=self.pause_playback).grid(row=0,column=2);ttk.Button(playback,text='Next',command=lambda:self.move_track(1)).grid(row=0,column=3,padx=3);self.position_scale=ttk.Scale(playback,from_=0,to=1000,variable=self.position,command=self.seek);self.position_scale.grid(row=0,column=4,sticky='ew',padx=8);ttk.Checkbutton(playback,text='Repeat',variable=self.repeat).grid(row=0,column=5);ttk.Checkbutton(playback,text='Shuffle',variable=self.shuffle).grid(row=0,column=6,padx=(5,0));ttk.Button(playback,text='Load Playlist',command=self.load_playlist).grid(row=1,column=0,columnspan=2,sticky='ew',pady=(5,0));ttk.Button(playback,text='Save Playlist',command=self.save_playlist).grid(row=1,column=2,columnspan=2,sticky='ew',padx=4,pady=(5,0));self.tree.bind('<<TreeviewSelect>>',self._select_track)

    def build_convert_tab(self,parent):
        parent.grid_columnconfigure(1,weight=1);self.convert_format=tk.StringVar(value='wav');self.convert_output=tk.StringVar();self.convert_bitrate=tk.StringVar(value='320k')
        ttk.Label(parent,text='Convert extracted or discovered sounds',font=('Segoe UI Semibold',14)).grid(row=0,column=0,columnspan=3,sticky='w',padx=10,pady=10);ttk.Label(parent,text='Output folder').grid(row=1,column=0,sticky='w',padx=10);ttk.Entry(parent,textvariable=self.convert_output).grid(row=1,column=1,sticky='ew');ttk.Button(parent,text='Browse',command=lambda:self.convert_output.set(filedialog.askdirectory() or self.convert_output.get())).grid(row=1,column=2,padx=8)
        ttk.Label(parent,text='Format').grid(row=2,column=0,sticky='w',padx=10,pady=8);ttk.Combobox(parent,textvariable=self.convert_format,values=('wav','mp3','ogg','flac','aac'),state='readonly').grid(row=2,column=1,sticky='ew');ttk.Label(parent,text='MP3 bitrate').grid(row=3,column=0,sticky='w',padx=10);ttk.Combobox(parent,textvariable=self.convert_bitrate,values=('128k','192k','256k','320k'),state='readonly').grid(row=3,column=1,sticky='ew');ttk.Button(parent,text='Convert Selected',command=lambda:self.convert_items(False)).grid(row=4,column=1,sticky='w',pady=12);ttk.Button(parent,text='Convert All',command=lambda:self.convert_items(True)).grid(row=4,column=1,sticky='e',pady=12)

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
    def _select_track(self,_event=None):
        selection=self.tree.selection()
        if selection:self.current_index=int(selection[0]);self.position.set(0)
    def _playable_file(self,item):
        if item.offset==-2:return item.relative_path
        folder=os.path.join(tempfile.gettempdir(),'AI_Generator_SoundPreview');os.makedirs(folder,exist_ok=True);target=self._extract(item,folder);self.temp_audio.append(target);return target
    def play_selected(self):
        if not self.items:return
        selection=self.tree.selection()
        if selection:self.current_index=int(selection[0])
        try:
            import pygame
            if not pygame.mixer.get_init():pygame.mixer.init()
            path=self._playable_file(self.items[self.current_index]);pygame.mixer.music.load(path)
            try:
                from pydub import AudioSegment
                self.current_duration=max(.1,len(AudioSegment.from_file(path))/1000)
            except Exception:self.current_duration=1.
            self.position_scale.configure(to=self.current_duration);pygame.mixer.music.play();self.play_paused=False;self.status.set(f'Playing {self.items[self.current_index].name}');self._poll_playback()
        except Exception as error:messagebox.showerror('Sound playback',f'Playback requires pygame and a supported codec.\n\n{error}')
    def pause_playback(self):
        try:
            import pygame
            if self.play_paused:pygame.mixer.music.unpause()
            else:pygame.mixer.music.pause()
            self.play_paused=not self.play_paused
        except Exception:pass
    def move_track(self,direction):
        if not self.items:return
        self.current_index=random.randrange(len(self.items)) if self.shuffle.get() else (self.current_index+direction)%len(self.items);self.tree.selection_set(str(self.current_index));self.tree.see(str(self.current_index));self.play_selected()
    def _poll_playback(self):
        try:
            import pygame
            if pygame.mixer.music.get_busy() or self.play_paused:
                position=max(0,pygame.mixer.music.get_pos())/1000;self.position.set(min(self.current_duration,position));self.parent.after(250,self._poll_playback)
            elif self.repeat.get():self.play_selected()
        except Exception:pass
    def seek(self,value):
        # Pygame seeking varies by codec. It is applied when supported and the
        # slider otherwise remains a playback-position indicator.
        if not getattr(self,'items',None):return
        try:
            import pygame
            if pygame.mixer.music.get_busy():pygame.mixer.music.set_pos(float(value))
        except Exception:pass
    def load_playlist(self):
        path=filedialog.askopenfilename(filetypes=[('M3U playlist','*.m3u *.m3u8'),('Text','*.txt')])
        if not path:return
        items=[];base=os.path.dirname(path)
        for line in open(path,'r',encoding='utf-8',errors='ignore'):
            value=line.strip()
            if not value or value.startswith('#'):continue
            source=value if os.path.isabs(value) else os.path.join(base,value)
            if os.path.isfile(source):items.append(SoundItem(os.path.basename(source),'Playlist audio',-2,os.path.getsize(source),source))
        self._finish(items,False);self.status.set(f'Loaded playlist with {len(items)} track(s).')
    def save_playlist(self):
        if not self.items:return
        path=filedialog.asksaveasfilename(defaultextension='.m3u8',filetypes=[('M3U8','*.m3u8')])
        if not path:return
        try:
            with open(path,'w',encoding='utf-8') as output:
                output.write('#EXTM3U\n')
                for item in self.items:output.write(self._playable_file(item)+'\n')
            self.status.set(f'Saved playlist: {path}')
        except Exception as error:messagebox.showerror('Playlist',str(error))
    def convert_items(self,all_items):
        selection=self.tree.selection();items=self.items if all_items else ([self.items[int(selection[0])]] if selection else [])
        folder=self.convert_output.get().strip()
        if not items or not folder:messagebox.showwarning('Convert','Scan sounds, select an item when needed, and choose an output folder.');return
        os.makedirs(folder,exist_ok=True);fmt=self.convert_format.get()
        def worker():
            converted=failed=0
            try:from pydub import AudioSegment
            except Exception as error:self.parent.after(0,lambda:messagebox.showerror('Convert',f'Pydub and FFmpeg are required.\n\n{error}'));return
            for item in items:
                try:
                    source=self._playable_file(item);audio=AudioSegment.from_file(source);target=os.path.join(folder,os.path.splitext(item.name)[0]+'.'+fmt);base,ext=os.path.splitext(target);number=1
                    while os.path.exists(target):target=f'{base}_{number}{ext}';number+=1
                    kwargs={'bitrate':self.convert_bitrate.get()} if fmt=='mp3' else {};audio.export(target,format=fmt,**kwargs);converted+=1
                except Exception:failed+=1
            self.parent.after(0,lambda:self.status.set(f'Converted {converted}; failed {failed}.'))
        threading.Thread(target=worker,daemon=True).start()

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
        if item.offset==-2:
            target=self._safe_path(folder,os.path.basename(item.relative_path));shutil.copy2(item.relative_path,target);return target
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
