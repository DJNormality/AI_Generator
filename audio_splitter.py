"""Dedicated vocal and instrumental separation tool for AI Generator."""
import glob, os, shutil, subprocess, sys, threading, tkinter as tk
from tkinter import filedialog, messagebox, ttk

from music_tool import configure_local_ffmpeg


class AudioSplitter:
    def __init__(self,parent,on_back=None):
        self.on_back=on_back;self.window=ttk.Frame(parent,style='App.TFrame');self.window.pack(fill='both',expand=True);self.process=None;self.stop_event=threading.Event();self._build()
    def _build(self):
        top=ttk.Frame(self.window,padding=12);top.pack(fill='x')
        if self.on_back:ttk.Button(top,text='← Back to Home',command=self.back).pack(side='left',padx=(0,8))
        ttk.Label(top,text='Audio Split',font=('Segoe UI Semibold',16)).pack(side='left')
        panel=ttk.Frame(self.window,padding=18);panel.pack(fill='both',expand=True,padx=14,pady=(0,10));panel.columnconfigure(1,weight=1)
        self.input=tk.StringVar();self.output=tk.StringVar();self.model=tk.StringVar(value='htdemucs');self.merge=tk.BooleanVar(value=False);self.status=tk.StringVar(value='Choose a song and output folder.')
        ttk.Label(panel,text='Song file').grid(row=0,column=0,sticky='w',pady=7);ttk.Entry(panel,textvariable=self.input).grid(row=0,column=1,sticky='ew',padx=8);ttk.Button(panel,text='Browse',command=self.pick_input).grid(row=0,column=2)
        ttk.Label(panel,text='Output folder').grid(row=1,column=0,sticky='w',pady=7);ttk.Entry(panel,textvariable=self.output).grid(row=1,column=1,sticky='ew',padx=8);ttk.Button(panel,text='Browse',command=self.pick_output).grid(row=1,column=2)
        ttk.Label(panel,text='Demucs model').grid(row=2,column=0,sticky='w',pady=7);ttk.Combobox(panel,textvariable=self.model,values=('htdemucs','htdemucs_ft','mdx_extra','mdx_extra_q'),state='readonly').grid(row=2,column=1,sticky='w',padx=8)
        ttk.Checkbutton(panel,text='Also create merged_stems.wav',variable=self.merge).grid(row=3,column=1,sticky='w',padx=8,pady=6)
        buttons=ttk.Frame(panel);buttons.grid(row=4,column=1,sticky='w',padx=8,pady=12);self.start_button=ttk.Button(buttons,text='Split Vocals + Instrumental',command=self.start);self.start_button.pack(side='left');self.stop_button=ttk.Button(buttons,text='Stop',command=self.stop,state='disabled');self.stop_button.pack(side='left',padx=6)
        self.progress=ttk.Progressbar(panel,mode='indeterminate',style='Accent.Horizontal.TProgressbar');self.progress.grid(row=5,column=0,columnspan=3,sticky='ew',pady=(8,4));ttk.Label(panel,textvariable=self.status).grid(row=6,column=0,columnspan=3,sticky='w')
        ttk.Label(panel,text='This tool keeps stem separation separate from the custom Song sequencer. Demucs produces vocals.wav and no_vocals.wav.',wraplength=760).grid(row=7,column=0,columnspan=3,sticky='w',pady=(14,0))
    def pick_input(self):
        p=filedialog.askopenfilename(filetypes=[('Audio','*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.wma'),('All files','*.*')]);
        if p:self.input.set(p);self.output.set(self.output.get() or os.path.join(os.path.dirname(p),os.path.splitext(os.path.basename(p))[0]+'_stems'))
    def pick_output(self):
        p=filedialog.askdirectory();
        if p:self.output.set(p)
    def start(self):
        source=self.input.get().strip();folder=self.output.get().strip()
        if not os.path.isfile(source):messagebox.showwarning('Audio Split','Choose a valid song file.');return
        if not folder:messagebox.showwarning('Audio Split','Choose an output folder.');return
        configure_local_ffmpeg();os.makedirs(folder,exist_ok=True);self.stop_event.clear();self.start_button.config(state='disabled');self.stop_button.config(state='normal');self.progress.start(12);self.status.set('Separating vocals and instrumental…');threading.Thread(target=self._worker,args=(source,folder),daemon=True).start()
    def _worker(self,source,folder):
        error=None
        try:
            command=[sys.executable,'-m','demucs','-n',self.model.get(),'--two-stems=vocals','-o',folder,source];self.process=subprocess.Popen(command)
            if self.process.wait():raise RuntimeError('Demucs failed. Run Install_Music_Tools.bat to repair the plugin.')
            roots=glob.glob(os.path.join(folder,'**','vocals.wav'),recursive=True);instrumentals=glob.glob(os.path.join(folder,'**','no_vocals.wav'),recursive=True)
            if not roots or not instrumentals:raise RuntimeError('Demucs completed but the output stems were not found.')
            shutil.copy2(roots[0],os.path.join(folder,'vocals.wav'));shutil.copy2(instrumentals[0],os.path.join(folder,'instrumental.wav'))
            if self.merge.get():
                from pydub import AudioSegment
                AudioSegment.from_file(roots[0]).overlay(AudioSegment.from_file(instrumentals[0])).export(os.path.join(folder,'merged_stems.wav'),format='wav')
        except Exception as exc:error=str(exc)
        self.window.after(0,lambda:self._done(folder,error))
    def _done(self,folder,error):
        self.progress.stop();self.start_button.config(state='normal');self.stop_button.config(state='disabled');self.process=None
        if error:self.status.set('Split failed.');messagebox.showerror('Audio Split',error)
        else:self.status.set(f'Finished: {folder}');messagebox.showinfo('Audio Split','Saved vocals.wav and instrumental.wav.')
    def stop(self):
        self.stop_event.set()
        if self.process and self.process.poll() is None:self.process.terminate()
        self.status.set('Stopping…')
    def back(self):
        if self.process and self.process.poll() is None:self.stop();return
        if self.on_back:self.on_back(self)

def open_audio_splitter(parent,on_back=None):return AudioSplitter(parent,on_back)
