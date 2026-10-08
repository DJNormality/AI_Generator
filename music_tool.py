"""Embedded music editor and stem/transcription helper for AI Generator."""
import glob, io, math, os, shutil, struct, subprocess, sys, tempfile, threading, tkinter as tk, wave
from tkinter import colorchooser, filedialog, messagebox, ttk

NOTES=('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')
SCALES={'Major':(0,2,4,5,7,9,11),'Natural Minor':(0,2,3,5,7,8,10),
        'Harmonic Minor':(0,2,3,5,7,8,11),'Melodic Minor':(0,2,3,5,7,9,11),
        'Major Pentatonic':(0,2,4,7,9),'Minor Pentatonic':(0,3,5,7,10),
        'Blues':(0,3,5,6,7,10),'Dorian':(0,2,3,5,7,9,10),
        'Phrygian':(0,1,3,5,7,8,10),'Lydian':(0,2,4,6,7,9,11),
        'Mixolydian':(0,2,4,5,7,9,10),'Chromatic':tuple(range(12))}
CHORDS={'Major':(0,4,7),'Minor':(0,3,7),'Diminished':(0,3,6),'Augmented':(0,4,8),
        'Sus2':(0,2,7),'Sus4':(0,5,7),'Major 7':(0,4,7,11),'Minor 7':(0,3,7,10),
        'Dominant 7':(0,4,7,10),'Minor 7♭5':(0,3,6,10),'Major 9':(0,4,7,11,14)}
GUITAR_CHORDS={'Major':(0,4,7),'Minor':(0,3,7),'Power 5':(0,7),'Diminished':(0,3,6),
 'Augmented':(0,4,8),'Sus2':(0,2,7),'Sus4':(0,5,7),'6':(0,4,7,9),'Minor 6':(0,3,7,9),
 '7':(0,4,7,10),'Major 7':(0,4,7,11),'Minor 7':(0,3,7,10),'Minor Major 7':(0,3,7,11),
 'Diminished 7':(0,3,6,9),'Minor 7 flat 5':(0,3,6,10),'Add9':(0,2,4,7),
 'Minor Add9':(0,2,3,7),'9':(0,2,4,7,10),'Major 9':(0,2,4,7,11),
 'Minor 9':(0,2,3,7,10),'11':(0,2,4,5,7,10),'Minor 11':(0,2,3,5,7,10),
 '13':(0,2,4,7,9,10),'Major 13':(0,2,4,7,9,11),'7 Sus4':(0,5,7,10),
 '7 flat 5':(0,4,6,10),'7 sharp 5':(0,4,8,10),'7 flat 9':(0,1,4,7,10),
 '7 sharp 9':(0,3,4,7,10),'6/9':(0,2,4,7,9)}
GUITAR_TUNING=(40,45,50,55,59,64)  # E2 A2 D3 G3 B3 E4
GUITAR_TUNINGS={'Standard E':(40,45,50,55,59,64),'Drop D':(38,45,50,55,59,64),
 'Half-step down':(39,44,49,54,58,63),'Whole-step down':(38,43,48,53,57,62),
 'DADGAD':(38,45,50,55,57,62),'Open G':(38,43,50,55,59,62),'Open D':(38,45,50,54,57,62)}

def configure_local_ffmpeg():
    app_dir=os.path.dirname(os.path.abspath(__file__));bin_dir=os.path.join(app_dir,'tools','ffmpeg','bin');ffmpeg=os.path.join(bin_dir,'ffmpeg.exe');ffprobe=os.path.join(bin_dir,'ffprobe.exe')
    if os.path.isfile(ffmpeg):
        os.environ['PATH']=bin_dir+os.pathsep+os.environ.get('PATH','')
        try:
            from pydub import AudioSegment
            AudioSegment.converter=ffmpeg
            if os.path.isfile(ffprobe):AudioSegment.ffprobe=ffprobe
        except ImportError:pass
    return ffmpeg if os.path.isfile(ffmpeg) else shutil.which('ffmpeg')

class MusicTool:
    def __init__(self,parent,on_back=None):
        self.on_back=on_back;self.window=ttk.Frame(parent,style='App.TFrame');self.window.pack(fill='both',expand=True)
        self.audio=None;self.path='';self.worker=None;self.process=None;self.stop_event=threading.Event();self.rolls={};self.mixer_channels=[None]*10;self.song_blocks=[];self._build()
    def _build(self):
        top=ttk.Frame(self.window,padding=10);top.pack(fill='x');ttk.Button(top,text='← Back to Home',command=self.back).pack(side='left',padx=(0,8))
        self.path_var=tk.StringVar();ttk.Entry(top,textvariable=self.path_var).pack(side='left',fill='x',expand=True);ttk.Button(top,text='Open Song',command=self.open_song).pack(side='left',padx=6)
        self.stop_button=ttk.Button(top,text='Stop',command=self.stop,state='disabled');self.stop_button.pack(side='left')
        pane=ttk.Panedwindow(self.window,orient='horizontal');pane.pack(fill='both',expand=True,padx=10,pady=(0,6));controls=ttk.Frame(pane,padding=8);preview=ttk.Frame(pane,padding=4);pane.add(controls,weight=0);pane.add(preview,weight=1)
        self.v={k:tk.StringVar(value=v) for k,v in {'start':'0','end':'0','speed':'1.00','gain':'0','channels':'Keep original','fade_in':'0','fade_out':'0','vocals':'Keep vocals','bitrate':'320k','midi_engine':'Built-in melody detection'}.items()};self.merge_stems=tk.BooleanVar(value=False)
        rows=[('Trim start (seconds)','start',None),('Trim end (0 = song end)','end',None),('Speed multiplier','speed',('0.25','0.50','0.75','1.00','1.25','1.50','2.00','3.00','4.00')),('Volume change (dB)','gain',None),('Channels','channels',('Keep original','Mono','Stereo','Left only','Right only')),('Fade in (seconds)','fade_in',None),('Fade out (seconds)','fade_out',None),('MP3 bitrate','bitrate',('128k','192k','256k','320k'))]
        for r,(label,key,values) in enumerate(rows):
            ttk.Label(controls,text=label).grid(row=r,column=0,sticky='w',pady=4);w=ttk.Combobox(controls,textvariable=self.v[key],values=values,state='readonly',width=24) if values else ttk.Entry(controls,textvariable=self.v[key],width=26);w.grid(row=r,column=1,sticky='ew',padx=(8,0),pady=4)
        controls.columnconfigure(1,weight=1);r=len(rows)
        ttk.Button(controls,text='Export Edited MP3',command=lambda:self.export_audio('mp3')).grid(row=r,column=0,columnspan=2,sticky='ew',pady=(10,3));ttk.Button(controls,text='Export Edited WAV',command=lambda:self.export_audio('wav')).grid(row=r+1,column=0,columnspan=2,sticky='ew',pady=3)
        ttk.Label(controls,text='Vocal and instrumental separation is available in the separate Audio Split tool.',wraplength=380,justify='left').grid(row=r+2,column=0,columnspan=2,sticky='w',pady=(8,0))
        view_tabs=ttk.Notebook(preview,style='Modern.TNotebook');view_tabs.pack(fill='both',expand=True);wave=ttk.Frame(view_tabs);piano_shell=ttk.Frame(view_tabs);guitar_shell=ttk.Frame(view_tabs);song=ttk.Frame(view_tabs);midi=ttk.Frame(view_tabs);view_tabs.add(wave,text='  Waveform  ');view_tabs.add(piano_shell,text='  Piano  ');view_tabs.add(guitar_shell,text='  Guitar  ');view_tabs.add(song,text='  Song  ');view_tabs.add(midi,text='  Midi  ')
        self.canvas=tk.Canvas(wave,bg='#020617',highlightthickness=0);self.canvas.pack(fill='both',expand=True);self.canvas.bind('<Configure>',lambda e:self.draw_waveform())
        self.info=tk.StringVar(value='No song loaded');ttk.Label(wave,textvariable=self.info).pack(fill='x',pady=(5,0));guitar=self._scroll_workspace(guitar_shell);self._build_piano(piano_shell);self._build_guitar(guitar);self._build_song(song);self._build_midi(midi)
        prog=ttk.Frame(self.window,padding=(10,0,10,8));prog.pack(fill='x');self.progress=tk.DoubleVar();self.progress_text=tk.StringVar(value='Ready');ttk.Progressbar(prog,variable=self.progress,maximum=100,style='Accent.Horizontal.TProgressbar').pack(side='left',fill='x',expand=True);ttk.Label(prog,textvariable=self.progress_text,width=34).pack(side='left',padx=(8,0))
    def _scroll_workspace(self,parent):
        canvas=tk.Canvas(parent,bg='#111827',highlightthickness=0);scroll=ttk.Scrollbar(parent,orient='vertical',command=canvas.yview);canvas.configure(yscrollcommand=scroll.set);canvas.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y');inner=ttk.Frame(canvas);window=canvas.create_window((0,0),window=inner,anchor='nw');inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')));canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width));canvas.bind('<MouseWheel>',lambda e:canvas.yview_scroll(-3 if e.delta>0 else 3,'units'));return inner
    def _build_midi(self,parent):
        panel=ttk.Frame(parent,padding=18);panel.pack(fill='both',expand=True);panel.columnconfigure(1,weight=1)
        ttk.Label(panel,text='Midi transcription',font=('Segoe UI Semibold',14)).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,14))
        ttk.Label(panel,text='Engine').grid(row=1,column=0,sticky='w');ttk.Combobox(panel,textvariable=self.v['midi_engine'],values=('Built-in melody detection','Basic Pitch AI'),state='readonly').grid(row=1,column=1,sticky='ew',padx=(10,0))
        ttk.Label(panel,text='Convert the loaded song into a note sequence. The Midi file contains detected notes, timing, and velocity—not the original audio.',wraplength=650,justify='left').grid(row=2,column=0,columnspan=2,sticky='w',pady=14)
        ttk.Button(panel,text='Transcribe loaded song to Midi',command=self.export_midi).grid(row=3,column=0,columnspan=2,sticky='ew')
    def _build_piano(self,parent):
        bar=ttk.Frame(parent,padding=(6,6,6,4));bar.pack(fill='x');self.root_note=tk.StringVar(value='C');self.scale_name=tk.StringVar(value='Major');self.chord_name=tk.StringVar(value='Major');self.piano_octave=tk.IntVar(value=3);self.pressed_note=None
        for label,var,values in [('Root',self.root_note,NOTES),('Scale',self.scale_name,tuple(SCALES)),('Chord',self.chord_name,tuple(CHORDS)),('Octave',self.piano_octave,tuple(range(1,7)))]:
            ttk.Label(bar,text=label).pack(side='left',padx=(7,3));box=ttk.Combobox(bar,textvariable=var,values=values,state='readonly',width=16 if label in ('Scale','Chord') else 5);box.pack(side='left');box.bind('<<ComboboxSelected>>',lambda e:self.draw_piano())
        self._build_roll(parent,'piano',12,self._piano_roll_notes)
        self.lesson=tk.StringVar();ttk.Label(parent,textvariable=self.lesson).pack(fill='x',padx=8,pady=(2,5))
        self.piano_visualizer=tk.Canvas(parent,bg='#17202b',highlightthickness=1,highlightbackground='#334155',height=150);self.piano_visualizer.pack(fill='x',padx=6,pady=(0,3));self.piano_visualizer.bind('<Configure>',lambda e:self.draw_piano_visualizer())
        self.piano=tk.Canvas(parent,bg='#0b1220',highlightthickness=0,height=125);self.piano.pack(fill='x',padx=6,pady=(0,6));self.piano.bind('<Configure>',lambda e:self.draw_piano());self.piano.bind('<Button-1>',self.piano_click)
    def _piano_roll_notes(self):return tuple(12*(self.piano_octave.get()+1)+i for i in range(12))
    def _guitar_roll_notes(self):
        tuning=self.current_tuning();shape=self.guitar_shape();capo=self.guitar_capo.get();return tuple(note+capo+fret for note,fret in zip(tuning,shape))
    def _build_roll(self,parent,name,rows,note_provider):
        box=ttk.Frame(parent,padding=(6,2,6,4));box.pack(fill='x');state={'cells':set(),'rows':rows,'provider':note_provider,'playing':False,'stop':threading.Event(),'step':-1,'note':'#22c55e','background':'#111827','measure':'#475569','bar':'#1e293b','volume':tk.IntVar(value=80),'pan':tk.IntVar(value=0),'bpm':tk.IntVar(value=120),'bars':tk.IntVar(value=1),'channel':tk.IntVar(value=1)};self.rolls[name]=state
        controls=ttk.Frame(box);controls.pack(fill='x');ttk.Button(controls,text='Play Loop',command=lambda:self.play_roll(name)).pack(side='left');ttk.Button(controls,text='Stop',command=lambda:self.stop_roll(name)).pack(side='left',padx=4)
        ttk.Label(controls,text='BPM').pack(side='left',padx=(8,3));ttk.Spinbox(controls,from_=30,to=300,textvariable=state['bpm'],width=5).pack(side='left');ttk.Label(controls,text='Bars').pack(side='left',padx=(7,3));bars=ttk.Spinbox(controls,from_=1,to=9999,textvariable=state['bars'],width=5,command=lambda n=name:self.draw_roll(n));bars.pack(side='left');bars.bind('<KeyRelease>',lambda e,n=name:self.draw_roll(n));ttk.Label(controls,text='Volume').pack(side='left',padx=(8,3));ttk.Scale(controls,from_=0,to=100,variable=state['volume'],orient='horizontal',length=70).pack(side='left');ttk.Label(controls,text='Pan').pack(side='left',padx=(8,3));ttk.Scale(controls,from_=-100,to=100,variable=state['pan'],orient='horizontal',length=70).pack(side='left')
        for label,key in [('Notes','note'),('Background','background'),('Measure','measure'),('Bars','bar')]:ttk.Button(controls,text=label,command=lambda n=name,k=key:self.roll_color(n,k)).pack(side='left',padx=(5,0))
        holder=ttk.Frame(box);holder.pack(fill='x');canvas=tk.Canvas(holder,bg=state['background'],height=118,highlightthickness=1,highlightbackground='#334155');canvas.pack(fill='x');state['canvas']=canvas;canvas.bind('<Configure>',lambda e,n=name:self.draw_roll(n));canvas.bind('<Button-1>',lambda e,n=name:self.roll_click(n,e))
        exports=ttk.Frame(box);exports.pack(fill='x',pady=(3,2));ttk.Label(exports,text='Save sequence:').pack(side='left')
        for label,ext in [('Export WAV','.wav'),('Export MP3','.mp3'),('Export MIDI','.midi')]:ttk.Button(exports,text=label,command=lambda n=name,e=ext:self.export_roll(n,e)).pack(side='left',padx=(5,0))
        ttk.Label(exports,text='Mixer channel').pack(side='left',padx=(12,3));ttk.Spinbox(exports,from_=1,to=10,textvariable=state['channel'],width=4).pack(side='left');ttk.Button(exports,text='Save to Mixer',command=lambda n=name:self.save_mixer_channel(n)).pack(side='left',padx=5)
    def roll_color(self,name,key):
        state=self.rolls[name];color=colorchooser.askcolor(color=state[key],title=f'Choose {key} color')[1]
        if color:state[key]=color;self.draw_roll(name)
    def draw_roll(self,name):
        state=self.rolls[name];c=state['canvas'];c.delete('all');steps=max(16,state['bars'].get()*16);rows=state['rows'];w=max(420,c.winfo_width());h=max(100,c.winfo_height());label_w=38;cw=(w-label_w)/steps;rh=h/rows;notes=state['provider']();c.configure(bg=state['background'],scrollregion=(0,0,w,h))
        for display_row in range(rows):
            row=rows-1-display_row;y=display_row*rh;note=notes[row];c.create_rectangle(0,y,label_w,y+rh,fill='#0f172a',outline='#334155');c.create_text(label_w-3,y+rh/2,text=NOTES[note%12],fill='#cbd5e1',anchor='e',font=('Segoe UI',7))
            for step in range(steps):
                x=label_w+step*cw;outline=state['measure'] if step%16==0 else state['bar'] if step%4==0 else '#243044';fill=state['note'] if (step,row) in state['cells'] else state['background'];c.create_rectangle(x,y,x+cw,y+rh,fill=fill,stipple='gray25' if (step,row) in state['cells'] else '',outline=outline)
        if state['step']>=0:
            x=label_w+state['step']*cw;c.create_rectangle(x,0,x+cw,h,outline='#f97316',width=2)
        if name=='piano':self.draw_piano_visualizer()
    def roll_click(self,name,event):
        state=self.rolls[name];c=state['canvas'];steps=max(16,state['bars'].get()*16);rows=state['rows'];label_w=38;w=max(420,c.winfo_width());h=max(100,c.winfo_height());cw=(w-label_w)/steps;rh=h/rows
        if event.x<label_w:return
        step=max(0,min(steps-1,int((event.x-label_w)/cw)));display_row=max(0,min(rows-1,int(event.y/rh)));row=rows-1-display_row;cell=(step,row)
        if cell in state['cells']:state['cells'].remove(cell)
        else:state['cells'].add(cell)
        self.draw_roll(name)
    def play_roll(self,name):
        state=self.rolls[name]
        if state['playing']:return
        state['playing']=True;state['stop'].clear()
        def loop():
            while not state['stop'].is_set():
                notes=state['provider']();step_seconds=60/max(30,state['bpm'].get())/4
                for step in range(max(16,state['bars'].get()*16)):
                    if state['stop'].is_set():break
                    state['step']=step;self.window.after(0,lambda n=name:self.draw_roll(n));playing=[notes[row] for s,row in state['cells'] if s==step]
                    if playing:self._play_notes(tuple(playing),max(60,int(step_seconds*900)),state['volume'].get(),state['pan'].get())
                    state['stop'].wait(step_seconds)
            state['playing']=False;state['step']=-1;self.window.after(0,lambda n=name:self.draw_roll(n))
        threading.Thread(target=loop,daemon=True).start()
    def stop_roll(self,name):self.rolls[name]['stop'].set()
    def render_roll(self,name):
        state=self.rolls[name];notes=state['provider']();steps=max(16,state['bars'].get()*16);step_seconds=60/max(30,state['bpm'].get())/4;rate=44100;total=int(rate*step_seconds*steps);left=[0.0]*total;right=[0.0]*total;volume=state['volume'].get()/100;pan=state['pan'].get()/100;lg=(1-pan)*.5;rg=(1+pan)*.5
        for step,row in state['cells']:
            note=notes[row];start=int(step*step_seconds*rate);length=min(int(step_seconds*.9*rate),total-start);freq=440*2**((note-69)/12)
            for i in range(length):
                env=min(1,i/(rate*.008))*max(0,1-i/max(1,length));sample=math.sin(2*math.pi*freq*i/rate)*.75+math.sin(4*math.pi*freq*i/rate)*.18;left[start+i]+=sample*env*volume*lg;right[start+i]+=sample*env*volume*rg
        pcm=bytearray()
        for l,r in zip(left,right):pcm.extend(struct.pack('<hh',int(max(-1,min(1,l))*30000),int(max(-1,min(1,r))*30000)))
        stream=io.BytesIO()
        with wave.open(stream,'wb') as wav:wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(bytes(pcm))
        return stream.getvalue(),step_seconds
    def export_roll(self,name,ext):
        state=self.rolls[name]
        if not state['cells']:messagebox.showwarning('Sequence','Click notes in the piano roll first.');return
        path=filedialog.asksaveasfilename(defaultextension=ext,filetypes=[(ext[1:].upper(),'*'+ext)])
        if not path:return
        try:
            if ext in ('.mid','.midi'):
                notes=state['provider']();events=[(step,step+1,notes[row]) for step,row in state['cells']];seconds=60/max(30,state['bpm'].get())/4;self._write_midi(path,events,seconds)
            else:
                data,_=self.render_roll(name)
                if ext=='.wav':open(path,'wb').write(data)
                else:
                    try:
                        from pydub import AudioSegment
                        AudioSegment.from_file(io.BytesIO(data),format='wav').export(path,format='mp3',bitrate=self.v['bitrate'].get())
                    except ImportError as e:raise RuntimeError('MP3 export requires: Scripts\\python.exe -m pip install pydub audioop-lts') from e
            self.progress_text.set(f'Exported {name} sequence: {os.path.basename(path)}')
        except Exception as e:messagebox.showerror('Sequence export',str(e))
    def save_mixer_channel(self,name):
        state=self.rolls[name];channel=max(1,min(10,state['channel'].get()))-1
        if not state['cells']:messagebox.showwarning('Mixer','Add notes before saving the pattern.');return
        self.mixer_channels[channel]={'name':f'{name.title()} Pattern','source':name,'cells':set(state['cells']),'notes':tuple(state['provider']()),'bars':state['bars'].get(),'bpm':state['bpm'].get(),'volume':state['volume'].get(),'pan':state['pan'].get()};self.progress_text.set(f'Saved {name} notes to mixer channel {channel+1}');self.draw_song()
    def _build_song(self,parent):
        top=ttk.Frame(parent,padding=7);top.pack(fill='x');self.song_channel=tk.IntVar(value=1);self.song_snap=tk.StringVar(value='1 bar');self.song_bars=tk.IntVar(value=16);self.song_stop=threading.Event();self.song_step=-1
        ttk.Label(top,text='Pattern channel').pack(side='left');ttk.Spinbox(top,from_=1,to=10,textvariable=self.song_channel,width=4).pack(side='left',padx=4);ttk.Label(top,text='Snap').pack(side='left',padx=(8,3));ttk.Combobox(top,textvariable=self.song_snap,values=('1/16','1/4','1 bar','Off'),state='readonly',width=8).pack(side='left');ttk.Label(top,text='Song bars').pack(side='left',padx=(8,3));bars=ttk.Spinbox(top,from_=1,to=9999,textvariable=self.song_bars,width=6,command=self.draw_song);bars.pack(side='left');ttk.Button(top,text='Play Song',command=self.play_song).pack(side='left',padx=(10,3));ttk.Button(top,text='Stop',command=lambda:self.song_stop.set()).pack(side='left')
        ttk.Label(parent,text='Select a saved mixer channel, then click the timeline to place its pattern. Drag a block to move it; right-click removes it.',padding=(7,0,7,4)).pack(fill='x')
        holder=ttk.Frame(parent);holder.pack(fill='both',expand=True,padx=7,pady=(0,6));self.song_canvas=tk.Canvas(holder,bg='#0b1220',highlightthickness=0);sx=ttk.Scrollbar(holder,orient='horizontal',command=self.song_canvas.xview);sy=ttk.Scrollbar(holder,orient='vertical',command=self.song_canvas.yview);self.song_canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set);self.song_canvas.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew');holder.rowconfigure(0,weight=1);holder.columnconfigure(0,weight=1);self.song_canvas.bind('<Configure>',lambda e:self.draw_song());self.song_canvas.bind('<Button-1>',self.song_click);self.song_canvas.bind('<B1-Motion>',self.song_drag);self.song_canvas.bind('<ButtonRelease-1>',lambda e:setattr(self,'song_drag_index',None));self.song_canvas.bind('<Button-3>',self.song_remove)
        bottom=ttk.Frame(parent,padding=7);bottom.pack(fill='x');ttk.Button(bottom,text='Clear Song',command=self.clear_song).pack(side='left')
        for label,ext in [('Export Song WAV','.wav'),('Export Song MP3','.mp3')]:ttk.Button(bottom,text=label,command=lambda e=ext:self.export_song(e)).pack(side='left',padx=(5,0))
    def song_snap_steps(self):return {'1/16':1,'1/4':4,'1 bar':16,'Off':1}[self.song_snap.get()]
    def draw_song(self):
        if not hasattr(self,'song_canvas'):return
        c=self.song_canvas;c.delete('all');steps=max(16,self.song_bars.get()*16);cw=24;rh=42;w=steps*cw;h=10*rh;c.configure(scrollregion=(0,0,w,h))
        for channel in range(10):
            y=channel*rh;c.create_text(4,y+rh/2,text=f'CH {channel+1}',fill='#cbd5e1',anchor='w');c.create_line(0,y,w,y,fill='#334155')
        for step in range(steps+1):c.create_line(step*cw,0,step*cw,h,fill='#475569' if step%16==0 else '#1e293b')
        colors=('#2563eb','#7c3aed','#db2777','#dc2626','#ea580c','#ca8a04','#16a34a','#0891b2','#4f46e5','#9333ea')
        for i,block in enumerate(self.song_blocks):
            ch=block['channel'];x=block['start']*cw;y=ch*rh+4;width=block['length']*cw;c.create_rectangle(x,y,x+width,y+rh-8,fill=colors[ch],outline='#f8fafc',tags=(f'block:{i}',));c.create_text(x+6,y+rh/2-4,text=block['pattern']['name'],fill='white',anchor='w',tags=(f'block:{i}',))
        if self.song_step>=0:c.create_line(self.song_step*cw,0,self.song_step*cw,h,fill='#f97316',width=3)
    def song_click(self,event):
        c=self.song_canvas;x=c.canvasx(event.x);y=c.canvasy(event.y);items=c.find_overlapping(x,y,x,y)
        for item in reversed(items):
            for tag in c.gettags(item):
                if tag.startswith('block:'):self.song_drag_index=int(tag.split(':')[1]);self.song_drag_offset=x-self.song_blocks[self.song_drag_index]['start']*24;return
        channel=max(0,min(9,self.song_channel.get()-1));pattern=self.mixer_channels[channel]
        if not pattern:messagebox.showwarning('Song',f'Mixer channel {channel+1} is empty. Save a piano or guitar pattern to it first.');return
        snap=self.song_snap_steps();step=max(0,round((x/24)/snap)*snap);self.song_blocks.append({'channel':channel,'start':step,'length':max(16,pattern['bars']*16),'pattern':pattern});self.draw_song()
    def song_drag(self,event):
        index=getattr(self,'song_drag_index',None)
        if index is None:return
        c=self.song_canvas;x=c.canvasx(event.x)-getattr(self,'song_drag_offset',0);y=c.canvasy(event.y);snap=self.song_snap_steps();self.song_blocks[index]['start']=max(0,round((x/24)/snap)*snap);self.song_blocks[index]['channel']=max(0,min(9,int(y/42)));self.draw_song()
    def song_remove(self,event):
        c=self.song_canvas;x=c.canvasx(event.x);y=c.canvasy(event.y)
        for item in reversed(c.find_overlapping(x,y,x,y)):
            for tag in c.gettags(item):
                if tag.startswith('block:'):self.song_blocks.pop(int(tag.split(':')[1]));self.draw_song();return
    def clear_song(self):self.song_blocks.clear();self.draw_song()
    def play_song(self):
        if not self.song_blocks:return
        self.song_stop.clear()
        def run():
            bpm=self.song_blocks[0]['pattern']['bpm'];duration=max(b['start']+b['length'] for b in self.song_blocks);seconds=60/max(30,bpm)/4
            for step in range(duration):
                if self.song_stop.is_set():break
                self.song_step=step;self.window.after(0,self.draw_song)
                for block in self.song_blocks:
                    local=step-block['start'];p=block['pattern']
                    if 0<=local<block['length']:
                        notes=[p['notes'][row] for s,row in p['cells'] if s==local]
                        if notes:self._play_notes(tuple(notes),max(60,int(seconds*900)),p['volume'],p['pan'])
                self.song_stop.wait(seconds)
            self.song_step=-1;self.window.after(0,self.draw_song)
        threading.Thread(target=run,daemon=True).start()
    def export_song(self,ext):
        if not self.song_blocks:messagebox.showwarning('Song','Place patterns in the Song timeline first.');return
        path=filedialog.asksaveasfilename(defaultextension=ext,filetypes=[(ext[1:].upper(),'*'+ext)])
        if not path:return
        try:
            bpm=self.song_blocks[0]['pattern']['bpm'];seconds=60/max(30,bpm)/4;rate=44100;steps=max(b['start']+b['length'] for b in self.song_blocks);total=int(rate*seconds*steps);left=[0.0]*total;right=[0.0]*total
            for block in self.song_blocks:
                p=block['pattern'];lg=(1-p['pan']/100)*.5;rg=(1+p['pan']/100)*.5;level=p['volume']/100
                for step,row in p['cells']:
                    absolute=block['start']+step
                    if absolute>=block['start']+block['length']:continue
                    note=p['notes'][row];start=int(absolute*seconds*rate);length=min(int(seconds*.9*rate),total-start);freq=440*2**((note-69)/12)
                    for i in range(length):
                        env=max(0,1-i/max(1,length));sample=math.sin(2*math.pi*freq*i/rate)*level*env;left[start+i]+=sample*lg;right[start+i]+=sample*rg
            pcm=bytearray()
            for l,r in zip(left,right):pcm.extend(struct.pack('<hh',int(max(-1,min(1,l))*30000),int(max(-1,min(1,r))*30000)))
            data=io.BytesIO()
            with wave.open(data,'wb') as wav:wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(bytes(pcm))
            if ext=='.wav':open(path,'wb').write(data.getvalue())
            else:
                from pydub import AudioSegment;AudioSegment.from_file(io.BytesIO(data.getvalue()),format='wav').export(path,format='mp3',bitrate=self.v['bitrate'].get())
            self.progress_text.set(f'Exported mixed song: {os.path.basename(path)}')
        except Exception as e:messagebox.showerror('Song export',str(e))
    def draw_piano(self):
        if not hasattr(self,'piano'):return
        c=self.piano;c.delete('all');w=max(300,c.winfo_width());h=max(105,c.winfo_height());root=NOTES.index(self.root_note.get());scale={(root+i)%12 for i in SCALES[self.scale_name.get()]};chord={(root+i)%12 for i in CHORDS[self.chord_name.get()]};base=12*(self.piano_octave.get()+1);white_notes=[n for n in range(base,base+36) if n%12 in (0,2,4,5,7,9,11)];white_w=w/len(white_notes)
        for i,n in enumerate(white_notes):
            x=i*white_w;pc=n%12;fill='#f97316' if n==self.pressed_note else '#ddd6fe' if pc in chord else '#dbeafe' if pc in scale else '#f8fafc';c.create_rectangle(x,0,x+white_w,h,fill=fill,outline='#111827',tags=(f'note:{n}','key'));c.create_text(x+white_w/2,h-11,text=NOTES[pc],fill='#111827',font=('Segoe UI Semibold',7))
        white_index={n:i for i,n in enumerate(white_notes)}
        for n in range(base,base+36):
            if n%12 not in (1,3,6,8,10):continue
            previous=max(x for x in white_notes if x<n);x=(white_index[previous]+1)*white_w-white_w*.31;pc=n%12;fill='#f97316' if n==self.pressed_note else '#7c3aed' if pc in chord else '#2563eb' if pc in scale else '#111827';c.create_rectangle(x,0,x+white_w*.62,h*.62,fill=fill,outline='#020617',tags=(f'note:{n}','key'))
        scale_notes=' '.join(NOTES[(root+i)%12] for i in SCALES[self.scale_name.get()]);chord_notes=' '.join(NOTES[(root+i)%12] for i in CHORDS[self.chord_name.get()]);self.lesson.set(f'{self.root_note.get()} {self.scale_name.get()} scale: {scale_notes}     |     {self.root_note.get()} {self.chord_name.get()} chord: {chord_notes}')
        self.draw_piano_visualizer()
    def draw_piano_visualizer(self):
        if not hasattr(self,'piano_visualizer') or 'piano' not in self.rolls:return
        c=self.piano_visualizer;c.delete('all');w=max(300,c.winfo_width());h=max(120,c.winfo_height());state=self.rolls['piano'];base=12*(self.piano_octave.get()+1);key_w=w/36;steps=max(16,state['bars'].get()*16);current=max(0,state['step'])
        for octave_line in range(4):c.create_line(octave_line*w/3,0,octave_line*w/3,h,fill='#475569',width=2)
        for n in range(37):c.create_line(n*key_w,0,n*key_w,h,fill='#243244')
        for beat in range(1,5):c.create_line(0,beat*h/5,w,beat*h/5,fill='#334155')
        for step,row in state['cells']:
            distance=(step-current)%steps
            if distance>15:continue
            note=state['provider']()[row];x=(note-base)*key_w
            if x<0 or x>=w:continue
            y=h-(distance+1)*(h/16);length=max(9,h/12);c.create_rectangle(x+2,max(1,y-length),x+key_w-2,min(h-1,y+4),fill='#a7f3b0',outline='#d1fae5')
        if self.pressed_note is not None and base<=self.pressed_note<base+36:
            x=(self.pressed_note-base)*key_w;c.create_rectangle(x+2,h*.58,x+key_w-2,h-3,fill='#f97316',outline='#fed7aa')
        c.create_line(0,h-2,w,h-2,fill='#f97316',width=3)
    def piano_click(self,event):
        items=self.piano.find_overlapping(event.x,event.y,event.x,event.y);note=None
        for item in reversed(items):
            for tag in self.piano.gettags(item):
                if tag.startswith('note:'):note=int(tag.split(':')[1]);break
            if note is not None:break
        if note is None:return
        self.pressed_note=note;self.draw_piano();self.progress_text.set(f'Piano note: {NOTES[note%12]}{note//12-1}')
        try:
            import winsound;frequency=int(440*2**((note-69)/12));threading.Thread(target=lambda:winsound.Beep(max(37,min(32767,frequency)),220),daemon=True).start()
        except Exception:pass
        self.window.after(260,lambda:self._release_note(note))
    def _release_note(self,note):
        if self.pressed_note==note:self.pressed_note=None;self.draw_piano()
    def _build_guitar(self,parent):
        bar=ttk.Frame(parent,padding=(6,6,6,4));bar.pack(fill='x');self.guitar_root=tk.StringVar(value='C');self.guitar_quality=tk.StringVar(value='Major');self.guitar_tuning=tk.StringVar(value='Standard E');self.guitar_capo=tk.IntVar(value=0);self.guitar_frets=tk.IntVar(value=12);self.guitar_active=None;self.guitar_seen=set();self.guitar_colors={'fretboard':'#5a2f1f','strings':'#e5e7eb','frets':'#c0c0c0','dots':'#f8fafc'}
        ttk.Label(bar,text='Root').pack(side='left');root=ttk.Combobox(bar,textvariable=self.guitar_root,values=NOTES,state='readonly',width=5);root.pack(side='left',padx=(4,10))
        ttk.Label(bar,text='Chord').pack(side='left');quality=ttk.Combobox(bar,textvariable=self.guitar_quality,values=tuple(GUITAR_CHORDS),state='readonly',width=20);quality.pack(side='left',padx=(4,10))
        ttk.Label(bar,text='Tuning').pack(side='left');tuning=ttk.Combobox(bar,textvariable=self.guitar_tuning,values=tuple(GUITAR_TUNINGS),state='readonly',width=15);tuning.pack(side='left',padx=(4,8));ttk.Label(bar,text='Capo').pack(side='left');capo=ttk.Spinbox(bar,from_=0,to=12,textvariable=self.guitar_capo,width=4,command=self._guitar_changed);capo.pack(side='left',padx=(4,8))
        ttk.Button(bar,text='Play Chord',command=self.play_guitar_chord).pack(side='left');ttk.Button(bar,text='Strum ↓',command=lambda:self.strum_guitar(False)).pack(side='left',padx=(5,0));ttk.Button(bar,text='Strum ↑',command=lambda:self.strum_guitar(True)).pack(side='left',padx=(5,0))
        root.bind('<<ComboboxSelected>>',lambda e:self._guitar_changed());quality.bind('<<ComboboxSelected>>',lambda e:self._guitar_changed());tuning.bind('<<ComboboxSelected>>',lambda e:self._guitar_changed());capo.bind('<KeyRelease>',lambda e:self._guitar_changed())
        colors=ttk.Frame(parent,padding=(6,0,6,2));colors.pack(fill='x');ttk.Label(colors,text='Guitar colors:').pack(side='left')
        for label,key in [('Fretboard','fretboard'),('Strings','strings'),('Frets','frets'),('Fret dots','dots')]:ttk.Button(colors,text=label,command=lambda k=key:self.guitar_color(k)).pack(side='left',padx=(5,0))
        self._build_roll(parent,'guitar',6,self._guitar_roll_notes)
        self.guitar_help=tk.StringVar();ttk.Label(parent,textvariable=self.guitar_help).pack(fill='x',padx=8,pady=(2,5))
        self.guitar=tk.Canvas(parent,bg='#0b1220',highlightthickness=0,height=220,cursor='hand2');self.guitar.pack(fill='both',expand=True,padx=6,pady=(0,6));self.guitar.bind('<Configure>',lambda e:self.draw_guitar());self.guitar.bind('<ButtonPress-1>',self.guitar_press);self.guitar.bind('<B1-Motion>',self.guitar_drag);self.guitar.bind('<ButtonRelease-1>',lambda e:self.guitar_seen.clear())
    def current_tuning(self):return GUITAR_TUNINGS[self.guitar_tuning.get()]
    def _guitar_changed(self):
        self.draw_guitar()
        if 'guitar' in self.rolls:self.draw_roll('guitar')
    def guitar_color(self,key):
        color=colorchooser.askcolor(color=self.guitar_colors[key],title=f'Choose guitar {key} color')[1]
        if color:self.guitar_colors[key]=color;self.draw_guitar()
    def guitar_shape(self):
        root=NOTES.index(self.guitar_root.get());pcs={(root+i)%12 for i in GUITAR_CHORDS[self.guitar_quality.get()]};shape=[];capo=self.guitar_capo.get()
        for string,open_note in enumerate(self.current_tuning()):
            choices=[f for f in range(13) if (open_note+capo+f)%12 in pcs]
            # Choose a compact playable inversion; the displayed notes show its voicing.
            fret=min(choices,key=lambda f:(f>5,f))
            shape.append(fret)
        return shape
    def draw_guitar(self):
        if not hasattr(self,'guitar'):return
        c=self.guitar;c.delete('all');w=max(500,c.winfo_width());h=max(260,c.winfo_height());left=48;right=14;top=45;bottom=h-35;frets=12;fw=(w-left-right)/(frets+1);sy=(bottom-top)/5;shape=self.guitar_shape()
        c.create_rectangle(left,top,w-right,bottom,fill=self.guitar_colors['fretboard'],outline='#94a3b8')
        # Subtle wood grain based on the supplied fretboard reference.
        for grain in range(18):
            y=top+(grain+1)*(bottom-top)/19;c.create_line(left,y,w-right,y,fill='#6b3b28',stipple='gray50')
        for fret in range(frets+2):
            x=left+fret*fw;c.create_line(x,top,x,bottom,fill=self.guitar_colors['frets'],width=4 if fret==1 else 2)
            if fret<=frets:c.create_text(x+fw/2,bottom+17,text=str(fret),fill='#cbd5e1')
        for marker in (3,5,7,9,12):
            x=left+(marker+.5)*fw;c.create_oval(x-5,(top+bottom)/2-5,x+5,(top+bottom)/2+5,fill=self.guitar_colors['dots'],outline='#9ca3af')
        tuning=self.current_tuning();capo=self.guitar_capo.get();labels=tuple(f'{NOTES[(n+capo)%12]}{(n+capo)//12-1}' for n in tuning)
        for s,open_note in enumerate(tuning):
            y=top+s*sy;c.create_line(left,y,w-right,y,fill=self.guitar_colors['strings'],width=1+(5-s)*.38);c.create_text(27,y,text=labels[s],fill='#e5e7eb')
            fret=shape[s];x=left+(fret+.5)*fw;fill='#f97316' if self.guitar_active==s else '#22c55e';c.create_oval(x-11,y-11,x+11,y+11,fill=fill,outline='#052e16');c.create_text(x,y,text=NOTES[(open_note+capo+fret)%12],fill='#07111f',font=('Segoe UI Semibold',8))
        chord_notes=' '.join(NOTES[(NOTES.index(self.guitar_root.get())+i)%12] for i in GUITAR_CHORDS[self.guitar_quality.get()]);frets_text=' '.join(str(f) for f in shape);self.guitar_help.set(f'{self.guitar_root.get()} {self.guitar_quality.get()} — {self.guitar_tuning.get()}, capo {capo} — notes: {chord_notes} — frets: {frets_text}. Click or drag across strings to strum.')
    def guitar_location(self,event):
        w=max(500,self.guitar.winfo_width());h=max(260,self.guitar.winfo_height());left=48;right=14;top=45;bottom=h-35;sy=(bottom-top)/5;fw=(w-left-right)/13
        string=max(0,min(5,round((event.y-top)/sy)));fret=max(0,min(12,int((event.x-left)/fw)))
        return string,fret
    def guitar_press(self,event):
        string,fret=self.guitar_location(event);note=self.current_tuning()[string]+self.guitar_capo.get()+fret;self.guitar_seen={string};self.guitar_active=string;self.draw_guitar();self._play_notes((note,));self.progress_text.set(f'Guitar note: {NOTES[note%12]}{note//12-1}')
    def guitar_drag(self,event):
        string,_=self.guitar_location(event)
        if string in self.guitar_seen:return
        self.guitar_seen.add(string);self.guitar_active=string;self.draw_guitar();shape=self.guitar_shape();self._play_notes((self.current_tuning()[string]+self.guitar_capo.get()+shape[string],),180)
    def play_guitar_chord(self):
        shape=self.guitar_shape();self._play_notes(tuple(note+self.guitar_capo.get()+fret for note,fret in zip(self.current_tuning(),shape)),700);self.progress_text.set(f'Playing {self.guitar_root.get()} {self.guitar_quality.get()}')
    def strum_guitar(self,reverse=False):
        order=list(range(6));
        if reverse:order.reverse()
        shape=self.guitar_shape()
        def run():
            for string in order:
                self.guitar_active=string;self.window.after(0,self.draw_guitar);self._play_notes((self.current_tuning()[string]+self.guitar_capo.get()+shape[string],),240);threading.Event().wait(.075)
            self.guitar_active=None;self.window.after(0,self.draw_guitar)
        threading.Thread(target=run,daemon=True).start()
    def _play_notes(self,notes,duration=450,volume=80,pan=0):
        def synth():
            try:
                import winsound
                rate=22050;count=int(rate*duration/1000);pcm=bytearray();level=max(0,min(100,volume))/100;position=max(-100,min(100,pan))/100;left_gain=(1-position)*.5;right_gain=(1+position)*.5
                for i in range(count):
                    t=i/rate;env=min(1,i/(rate*.012))*max(0,1-i/count);sample=0
                    for note in notes:
                        freq=440*2**((note-69)/12);sample+=math.sin(2*math.pi*freq*t)+.25*math.sin(4*math.pi*freq*t)
                    value=25000*level*env*sample/max(1,len(notes));pcm.extend(struct.pack('<hh',int(max(-32767,min(32767,value*left_gain))),int(max(-32767,min(32767,value*right_gain)))))
                stream=io.BytesIO()
                with wave.open(stream,'wb') as wav:wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(bytes(pcm))
                winsound.PlaySound(stream.getvalue(),winsound.SND_MEMORY)
            except Exception:pass
        threading.Thread(target=synth,daemon=True).start()
    def open_song(self):
        p=filedialog.askopenfilename(title='Open song',filetypes=[('Audio','*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.wma'),('All files','*.*')])
        if not p:return
        try:
            ffmpeg=configure_local_ffmpeg()
            from pydub import AudioSegment
            if not ffmpeg and os.path.splitext(p)[1].lower()!='.wav':raise RuntimeError('FFmpeg was not found. Run Install_Music_Tools.bat, then restart AI Generator.')
            self.audio=AudioSegment.from_file(p);self.path=p;self.path_var.set(p);self.v['end'].set(f'{len(self.audio)/1000:.3f}');self.info.set(f'{len(self.audio)/1000:.2f} sec | {self.audio.frame_rate:,} Hz | {self.audio.channels} channel(s) | {self.audio.sample_width*8}-bit');self.draw_waveform()
        except ImportError as e:messagebox.showerror('Music',f'Audio support could not load.\n\nRun Install_Music_Tools.bat from the main AI_Generator folder, then restart the app.\n\nPython: {sys.executable}\nDetails: {e}')
        except Exception as e:messagebox.showerror('Open song',f'{e}\n\nFFmpeg is required for MP3/M4A/AAC and many other formats.')
    def draw_waveform(self):
        self.canvas.delete('all')
        if not self.audio:return
        w=max(10,self.canvas.winfo_width());h=max(10,self.canvas.winfo_height());samples=self.audio.set_channels(1).get_array_of_samples();step=max(1,len(samples)//w);peak=max(1,2**(8*self.audio.sample_width-1));mid=h/2
        points=[]
        for x in range(w):
            part=samples[x*step:min(len(samples),(x+1)*step)]
            amp=max((abs(v) for v in part),default=0)/peak*(h*.46);points.extend((x,mid-amp,x,mid+amp))
        for i in range(0,len(points),4):self.canvas.create_line(*points[i:i+4],fill='#22c55e')
    def edited(self,audio=None):
        if audio is None:audio=self.audio
        if audio is None:raise ValueError('Open a song first.')
        start=max(0,float(self.v['start'].get() or 0));end=float(self.v['end'].get() or 0);end=end if end>0 else len(audio)/1000
        if end<=start:raise ValueError('Trim end must be after trim start.')
        out=audio[int(start*1000):min(len(audio),int(end*1000))];speed=float(self.v['speed'].get());
        if speed<=0:raise ValueError('Speed must be greater than zero.')
        if speed!=1:out=out._spawn(out.raw_data,overrides={'frame_rate':int(out.frame_rate*speed)}).set_frame_rate(audio.frame_rate)
        out+=float(self.v['gain'].get() or 0);ch=self.v['channels'].get()
        if ch=='Mono':out=out.set_channels(1)
        elif ch=='Stereo':out=out.set_channels(2)
        elif ch in ('Left only','Right only'):
            parts=out.split_to_mono();out=parts[0 if ch=='Left only' else min(1,len(parts)-1)].set_channels(1)
        fi=max(0,int(float(self.v['fade_in'].get() or 0)*1000));fo=max(0,int(float(self.v['fade_out'].get() or 0)*1000));return out.fade_in(min(fi,len(out))).fade_out(min(fo,len(out)))
    def center_cancel(self,audio):
        if audio.channels<2:return audio
        left,right=audio.split_to_mono()[:2];return left.overlay(right.invert_phase()).set_channels(2)
    def begin(self,text,target):
        if self.worker and self.worker.is_alive():return
        self.stop_event.clear();self.stop_button.config(state='normal');self.progress.set(5);self.progress_text.set(text);self.worker=threading.Thread(target=target,daemon=True);self.worker.start()
    def finish(self,text,error=None):
        self.stop_button.config(state='disabled');self.progress.set(0 if error else 100);self.progress_text.set('Error' if error else text)
        if error:messagebox.showerror('Music',str(error))
    def export_audio(self,fmt):
        if not self.audio:messagebox.showwarning('Music','Open a song first.');return
        p=filedialog.asksaveasfilename(defaultextension='.'+fmt,filetypes=[(fmt.upper(),'*.'+fmt)])
        if not p:return
        def work():
            try:
                audio=self.edited();mode=self.v['vocals'].get()
                if mode=='Center-cancel vocals':audio=self.center_cancel(audio)
                elif mode=='Demucs instrumental':audio=self._demucs_instrumental()
                if self.stop_event.is_set():return self.window.after(0,lambda:self.finish('Stopped'))
                args={'format':fmt};
                if fmt=='mp3':args['bitrate']=self.v['bitrate'].get()
                audio.export(p,**args);self.window.after(0,lambda:self.finish(f'Exported {os.path.basename(p)}'))
            except Exception as e:self.window.after(0,lambda e=e:self.finish('',e))
        self.begin('Editing and exporting…',work)
    def _run_demucs(self,folder):
        cmd=[sys.executable,'-m','demucs','--two-stems=vocals','-o',folder,self.path];self.process=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT,text=True)
        while self.process.poll() is None:
            if self.stop_event.wait(.2):self.process.terminate();raise RuntimeError('Operation stopped.')
        if self.process.returncode:raise RuntimeError('Demucs failed. Install it with: Scripts\\python.exe -m pip install demucs')
        matches=glob.glob(os.path.join(folder,'**','no_vocals.wav'),recursive=True);vocals=glob.glob(os.path.join(folder,'**','vocals.wav'),recursive=True)
        if not matches:raise RuntimeError('Demucs finished but no stems were found.')
        return matches[0],vocals[0] if vocals else None
    def _demucs_instrumental(self):
        from pydub import AudioSegment
        with tempfile.TemporaryDirectory() as d:
            instrumental,_=self._run_demucs(d);return self.edited(AudioSegment.from_file(instrumental))
    def split_vocals(self):
        if not self.path:messagebox.showwarning('Music','Open a song first.');return
        folder=filedialog.askdirectory(title='Save vocal stems')
        if not folder:return
        def work():
            try:
                with tempfile.TemporaryDirectory() as d:
                    instrumental,vocals=self._run_demucs(d);shutil.copy2(instrumental,os.path.join(folder,'instrumental.wav'))
                    if vocals:shutil.copy2(vocals,os.path.join(folder,'vocals.wav'))
                    if vocals and self.merge_stems.get():
                        from pydub import AudioSegment
                        music=AudioSegment.from_file(instrumental);voice=AudioSegment.from_file(vocals);music.overlay(voice).export(os.path.join(folder,'merged_stems.wav'),format='wav')
                self.window.after(0,lambda:self.finish('Vocal split complete'))
            except Exception as e:self.window.after(0,lambda e=e:self.finish('',e))
        self.begin('AI vocal separation…',work)
    def export_midi(self):
        if not self.path:messagebox.showwarning('Music','Open a song first.');return
        p=filedialog.asksaveasfilename(defaultextension='.mid',filetypes=[('MIDI','*.mid *.midi')])
        if not p:return
        def work():
            try:
                if self.v['midi_engine'].get()=='Built-in melody detection':
                    self._simple_midi(self.edited(),p)
                else:
                    try:from basic_pitch.inference import predict_and_save
                    except ImportError as e:raise RuntimeError('Basic Pitch AI requires a compatible Python build and: Scripts\\python.exe -m pip install basic-pitch') from e
                    with tempfile.TemporaryDirectory() as d:
                        source=os.path.join(d,'edited.wav');self.edited().export(source,format='wav')
                        predict_and_save([source],d,True,False,False,False)
                        found=glob.glob(os.path.join(d,'*.mid'))
                        if not found:raise RuntimeError('No MIDI file was produced.')
                        shutil.copy2(found[0],p)
                self.window.after(0,lambda:self.finish('MIDI transcription complete'))
            except Exception as e:self.window.after(0,lambda e=e:self.finish('',e))
        self.begin('Transcribing notes to MIDI…',work)
    def _simple_midi(self,audio,path):
        """Create a monophonic MIDI melody using windowed FFT pitch estimates."""
        import math,numpy as np
        mono=audio.set_channels(1).set_frame_rate(16000);samples=np.asarray(mono.get_array_of_samples(),dtype=np.float32)
        if not len(samples):raise ValueError('The selected audio is empty.')
        samples/=max(1.0,float(2**(8*mono.sample_width-1)));rate=mono.frame_rate;hop=int(rate*.10);window=int(rate*.20);notes=[]
        for start in range(0,max(1,len(samples)-window+1),hop):
            if self.stop_event.is_set():raise RuntimeError('Operation stopped.')
            frame=samples[start:start+window]
            if len(frame)<window or float(np.sqrt(np.mean(frame*frame)))<.012:notes.append(None);continue
            spectrum=np.abs(np.fft.rfft(frame*np.hanning(window)));freqs=np.fft.rfftfreq(window,1/rate);valid=(freqs>=55)&(freqs<=2000)
            if not np.any(valid):notes.append(None);continue
            frequency=float(freqs[valid][int(np.argmax(spectrum[valid]))]);note=int(round(69+12*math.log2(frequency/440.0)));notes.append(max(0,min(127,note)))
        events=[];active=None;begin=0
        for i,note in enumerate(notes+[None]):
            if note==active:continue
            if active is not None and i-begin>=2:events.append((begin,i,active))
            active=note;begin=i
        self._write_midi(path,events,seconds_per_step=hop/rate)
    def _write_midi(self,path,events,seconds_per_step=.1):
        ticks_per_quarter=480;ticks_per_second=960
        def variable(n):
            values=[n&127];n>>=7
            while n:values.append((n&127)|128);n>>=7
            return bytes(reversed(values))
        timeline=[]
        for start,end,note in events:
            timeline.append((round(start*seconds_per_step*ticks_per_second),1,note));timeline.append((round(end*seconds_per_step*ticks_per_second),0,note))
        timeline.sort(key=lambda x:(x[0],x[1]));track=bytearray(b'\x00\xff\x51\x03\x07\xa1\x20');last=0
        for tick,on,note in timeline:
            track.extend(variable(max(0,tick-last)));track.extend(bytes((0x90 if on else 0x80,note,88 if on else 0)));last=tick
        track.extend(b'\x00\xff\x2f\x00');header=b'MThd'+(6).to_bytes(4,'big')+(0).to_bytes(2,'big')+(1).to_bytes(2,'big')+ticks_per_quarter.to_bytes(2,'big')
        with open(path,'wb') as stream:stream.write(header+b'MTrk'+len(track).to_bytes(4,'big')+track)
    def stop(self):
        self.stop_event.set();self.progress_text.set('Stopping…')
        for state in self.rolls.values():state['stop'].set()
        if self.process and self.process.poll() is None:
            try:self.process.terminate()
            except:pass
    def back(self):
        for state in self.rolls.values():state['stop'].set()
        if self.worker and self.worker.is_alive():self.stop();self.window.after(100,self.back);return
        if self.on_back:self.on_back(self)

def open_music_tool(parent,on_back=None):return MusicTool(parent,on_back)
