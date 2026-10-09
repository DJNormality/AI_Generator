"""Offline AI Generator music creation workspace backed by local ACE-Step."""
from __future__ import annotations
import os, subprocess, threading, tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from ace_step_client import AceStepError, generate, health

class LocalMusicCreateTool:
    def __init__(self,parent):
        self.parent=parent;self.stop_event=threading.Event();self.outputs=[];self.player_ready=False
        self.server=tk.StringVar(value='http://127.0.0.1:8001');self.title=tk.StringVar();self.style=tk.StringVar();self.duration=tk.IntVar(value=60);self.bpm=tk.IntVar(value=120);self.key_scale=tk.StringVar(value='C Major');self.time_signature=tk.StringVar(value='4');self.language=tk.StringVar(value='en');self.format=tk.StringVar(value='wav');self.model=tk.StringVar(value='acestep-v15-turbo');self.steps=tk.IntVar(value=8);self.seed=tk.IntVar(value=-1);self.random_seed=tk.BooleanVar(value=True);self.use_lm=tk.BooleanVar(value=False);self.instrumental=tk.BooleanVar(value=False);self.status=tk.StringVar(value='Local model server is not checked.');self.progress=tk.DoubleVar(value=0);self.output_dir=tk.StringVar(value=os.path.join(os.path.dirname(os.path.abspath(__file__)),'outputs','music'))
        self._build()
    def _build(self):
        root=ttk.Frame(self.parent,style='Panel.TFrame',padding=12);root.pack(fill='both',expand=True);root.columnconfigure(1,weight=1);root.rowconfigure(5,weight=1)
        ttk.Label(root,text='AI Generator Music Create',font=('Segoe UI Semibold',16)).grid(row=0,column=0,columnspan=4,sticky='w')
        ttk.Label(root,text='Generate complete tracks locally. After setup and model download, no internet connection or API key is required.',style='Hint.TLabel',wraplength=920,justify='left').grid(row=1,column=0,columnspan=4,sticky='ew',pady=(2,10))
        server=ttk.Frame(root);server.grid(row=2,column=0,columnspan=4,sticky='ew',pady=(0,7));server.columnconfigure(1,weight=1);ttk.Label(server,text='Local server').grid(row=0,column=0,sticky='w');ttk.Entry(server,textvariable=self.server).grid(row=0,column=1,sticky='ew',padx=7);ttk.Button(server,text='Start Local Engine',command=self.start_server).grid(row=0,column=2,padx=(0,5));ttk.Button(server,text='Check',command=self.check_server).grid(row=0,column=3)
        basic=ttk.Frame(root);basic.grid(row=3,column=0,columnspan=4,sticky='ew',pady=(0,7));basic.columnconfigure(1,weight=1);ttk.Label(basic,text='Track title').grid(row=0,column=0,sticky='w');ttk.Entry(basic,textvariable=self.title).grid(row=0,column=1,sticky='ew',padx=7);ttk.Label(basic,text='Style / genre').grid(row=0,column=2,sticky='w');ttk.Entry(basic,textvariable=self.style,width=32).grid(row=0,column=3,sticky='ew',padx=(7,0))
        options=ttk.Frame(root);options.grid(row=4,column=0,columnspan=4,sticky='ew',pady=(0,7))
        fields=(('Length',self.duration,(10,600,5)),('BPM',self.bpm,(30,300,1)),('Key',self.key_scale,('C Major','C Minor','D Major','D Minor','E Major','E Minor','F Major','F Minor','G Major','G Minor','A Major','A Minor','B Major','B Minor')),('Meter',self.time_signature,('2','3','4','6')),('Language',self.language,('en','es','fr','de','it','pt','ja','zh','ko')),('Format',self.format,('wav','mp3','flac','opus')),('Steps',self.steps,(1,20,1)))
        for column,(label,var,values) in enumerate(fields):
            ttk.Label(options,text=label).grid(row=0,column=column*2,sticky='w',padx=(0,3));widget=ttk.Spinbox(options,from_=values[0],to=values[1],increment=values[2],textvariable=var,width=6) if isinstance(values[0],int) else ttk.Combobox(options,textvariable=var,values=values,state='readonly',width=9);widget.grid(row=0,column=column*2+1,sticky='w',padx=(0,8))
        editor=ttk.Panedwindow(root,orient='horizontal');editor.grid(row=5,column=0,columnspan=4,sticky='nsew');left=ttk.Frame(editor,padding=(0,0,5,0));right=ttk.Frame(editor,padding=(5,0,0,0));editor.add(left,weight=1);editor.add(right,weight=1)
        ttk.Label(left,text='Track description').pack(anchor='w');self.prompt=tk.Text(left,height=12,wrap='word',undo=True,bg='#0f172a',fg='#e2e8f0',insertbackground='#e2e8f0',selectbackground='#2563eb',relief='flat',padx=8,pady=8);self.prompt.pack(fill='both',expand=True,pady=(4,0))
        ttk.Label(right,text='Lyrics (use [Verse], [Chorus], [Bridge])').pack(anchor='w');self.lyrics=tk.Text(right,height=12,wrap='word',undo=True,bg='#0f172a',fg='#e2e8f0',insertbackground='#e2e8f0',selectbackground='#2563eb',relief='flat',padx=8,pady=8);self.lyrics.pack(fill='both',expand=True,pady=(4,0))
        controls=ttk.Frame(root);controls.grid(row=6,column=0,columnspan=4,sticky='ew',pady=(8,0));ttk.Checkbutton(controls,text='Instrumental',variable=self.instrumental).pack(side='left');ttk.Checkbutton(controls,text='Use local 0.6B planner (higher quality / more VRAM)',variable=self.use_lm).pack(side='left',padx=8);ttk.Checkbutton(controls,text='Random seed',variable=self.random_seed).pack(side='left');ttk.Entry(controls,textvariable=self.seed,width=10).pack(side='left',padx=(3,8));self.generate_button=ttk.Button(controls,text='Generate Track',command=self.start_generation);self.generate_button.pack(side='left');self.stop_button=ttk.Button(controls,text='Stop',command=self.stop,state='disabled');self.stop_button.pack(side='left',padx=5);ttk.Button(controls,text='Play Result',command=self.play).pack(side='left');ttk.Button(controls,text='Stop Audio',command=self.stop_audio).pack(side='left',padx=5);ttk.Button(controls,text='Open Output Folder',command=self.open_output).pack(side='right')
        out=ttk.Frame(root);out.grid(row=7,column=0,columnspan=4,sticky='ew',pady=(8,0));out.columnconfigure(1,weight=1);ttk.Label(out,text='Output folder').grid(row=0,column=0,sticky='w');ttk.Entry(out,textvariable=self.output_dir).grid(row=0,column=1,sticky='ew',padx=6);ttk.Button(out,text='Browse',command=self.choose_output).grid(row=0,column=2)
        footer=ttk.Frame(root);footer.grid(row=8,column=0,columnspan=4,sticky='ew',pady=(8,0));footer.columnconfigure(0,weight=1);ttk.Progressbar(footer,variable=self.progress,maximum=100,style='Accent.Horizontal.TProgressbar').grid(row=0,column=0,sticky='ew');ttk.Label(footer,textvariable=self.status,width=48).grid(row=0,column=1,sticky='w',padx=(8,0))
    def start_server(self):
        script=os.path.join(os.path.dirname(os.path.abspath(__file__)),'Start_ACE_Step_Local.bat')
        if not os.path.isfile(script):messagebox.showerror('Local Music','Start_ACE_Step_Local.bat is missing.');return
        try:os.startfile(script);self.status.set('Local engine is starting. First launch may download model files.')
        except Exception as error:messagebox.showerror('Local Music',str(error))
    def check_server(self):
        def worker():
            try:health(self.server.get().strip());self.parent.after(0,lambda:self.status.set('Local ACE-Step engine is connected and ready.'))
            except Exception as error:
                message=str(error);self.parent.after(0,lambda:self.status.set(message))
        threading.Thread(target=worker,daemon=True).start()
    def choose_output(self):
        folder=filedialog.askdirectory(title='Choose generated music folder')
        if folder:self.output_dir.set(folder)
    def _description(self):
        prompt=self.prompt.get('1.0','end-1c').strip();style=self.style.get().strip();title=self.title.get().strip();parts=[]
        if title:parts.append(f'Track titled {title}')
        if style:parts.append(style)
        if prompt:parts.append(prompt)
        if self.instrumental.get():parts.append('instrumental, no vocals')
        return ', '.join(parts)
    def start_generation(self):
        if not self._description():messagebox.showwarning('Local Music','Enter a track description or style.');return
        self.stop_event.clear();self.generate_button.configure(state='disabled');self.stop_button.configure(state='normal');self.progress.set(1)
        def report(value,text):self.parent.after(0,self.progress.set,value);self.parent.after(0,self.status.set,text)
        def worker():
            try:
                lyrics='' if self.instrumental.get() else self.lyrics.get('1.0','end-1c').strip()
                self.outputs=generate(self.server.get().strip(),self.output_dir.get().strip(),self._description(),lyrics,self.duration.get(),self.bpm.get(),self.key_scale.get(),self.time_signature.get(),self.format.get(),self.seed.get(),self.random_seed.get(),self.steps.get(),self.model.get(),self.language.get(),self.use_lm.get(),self.stop_event,report)
                self.parent.after(0,self._done)
            except Exception as error:self.parent.after(0,self._failed,str(error))
        threading.Thread(target=worker,daemon=True).start()
    def _done(self):
        self.generate_button.configure(state='normal');self.stop_button.configure(state='disabled');self.progress.set(100);self.status.set(f'Created {len(self.outputs)} local track(s): {os.path.basename(self.outputs[0])}')
    def _failed(self,error):
        self.generate_button.configure(state='normal');self.stop_button.configure(state='disabled');self.progress.set(0);self.status.set(error);messagebox.showerror('Local Music',error)
    def stop(self):self.stop_event.set();self.status.set('Stopping progress monitoring…')
    def play(self):
        if not self.outputs or not os.path.isfile(self.outputs[-1]):messagebox.showwarning('Local Music','Generate a track first.');return
        try:
            import pygame
            if not self.player_ready:pygame.mixer.init();self.player_ready=True
            pygame.mixer.music.load(self.outputs[-1]);pygame.mixer.music.play();self.status.set(f'Playing {os.path.basename(self.outputs[-1])}')
        except Exception as error:messagebox.showerror('Local Music',f'Playback failed: {error}')
    def stop_audio(self):
        try:
            if self.player_ready:
                import pygame;pygame.mixer.music.stop()
            self.status.set('Playback stopped.')
        except Exception:pass
    def open_output(self):
        folder=self.output_dir.get().strip();os.makedirs(folder,exist_ok=True)
        try:os.startfile(folder)
        except AttributeError:subprocess.Popen(['xdg-open',folder])

def build_local_music_create(parent):return LocalMusicCreateTool(parent)
