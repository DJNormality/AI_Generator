"""Embedded non-destructive video timeline and FFmpeg exporter for AI Generator."""
import json, os, subprocess, tempfile, threading, tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk

@dataclass
class Clip:
    path:str;duration:float;source_in:float=0.;source_out:float=0.;start:float=0.
    def length(self):return max(0.05,(self.source_out or self.duration)-self.source_in)

class VideoTool:
    def __init__(self,parent,on_back=None):
        self.on_back=on_back;self.window=ttk.Frame(parent,style='App.TFrame');self.window.pack(fill='both',expand=True);self.clips=[];self.selected=None;self.drag=None;self.stop_event=threading.Event();self.process=None;self._build()
    def _build(self):
        top=ttk.Frame(self.window,padding=8);top.pack(fill='x')
        if self.on_back:ttk.Button(top,text='← Back to Home',command=self.back).pack(side='left')
        ttk.Button(top,text='Add Clips',command=self.add_clips).pack(side='left',padx=5);ttk.Button(top,text='Remove',command=self.remove_clip).pack(side='left');ttk.Button(top,text='Clear All',command=self.clear_all).pack(side='left',padx=5);ttk.Button(top,text='Export MP4',command=self.export_mp4).pack(side='right');self.stop_button=ttk.Button(top,text='Stop',command=self.stop,state='disabled');self.stop_button.pack(side='right',padx=5)
        pane=ttk.Panedwindow(self.window,orient='horizontal');pane.pack(fill='both',expand=True,padx=8,pady=(0,6));settings=ttk.Frame(pane,padding=7);editor=ttk.Frame(pane);pane.add(settings,weight=0);pane.add(editor,weight=1)
        defaults={'crop_x':'0','crop_y':'0','crop_w':'0','crop_h':'0','width':'1920','height':'1080','rotate':'0','zoom':'1.0','speed':'1.0','fade_in':'0','fade_out':'0','brightness':'0','contrast':'1.0','saturation':'1.0','hue':'0','filter':'None','cut':'0','snap':'1 second','custom_move':'0'};self.v={k:tk.StringVar(value=v) for k,v in defaults.items()}
        rows=[('Crop X','crop_x',None),('Crop Y','crop_y',None),('Crop width (0=off)','crop_w',None),('Crop height (0=off)','crop_h',None),('Output width','width',None),('Output height','height',None),('Rotate','rotate',('0','90','180','270')),('Zoom','zoom',('0.5','0.75','1.0','1.25','1.5','2.0','3.0')),('Speed','speed',('0.25','0.5','0.75','1.0','1.25','1.5','2.0','4.0')),('Fade in seconds','fade_in',None),('Fade out seconds','fade_out',None),('Brightness','brightness',None),('Contrast','contrast',None),('Saturation','saturation',None),('Hue degrees','hue',None),('Filter','filter',('None','Grayscale','Sepia','Vintage','Cool','Warm','Sharpen','Blur')),('Cut at seconds','cut',None),('Timeline snap','snap',('1 frame','0.1 second','0.5 second','1 second','Off')),('Custom move seconds','custom_move',None)]
        for r,(label,key,values) in enumerate(rows):ttk.Label(settings,text=label).grid(row=r,column=0,sticky='w',pady=2);w=ttk.Combobox(settings,textvariable=self.v[key],values=values,state='readonly',width=17) if values else ttk.Entry(settings,textvariable=self.v[key],width=19);w.grid(row=r,column=1,sticky='ew',padx=(7,0),pady=2)
        r=len(rows);ttk.Button(settings,text='Cut Selected',command=self.cut_selected).grid(row=r,column=0,columnspan=2,sticky='ew',pady=(7,2));ttk.Button(settings,text='Move Selected',command=self.move_custom).grid(row=r+1,column=0,columnspan=2,sticky='ew',pady=2);ttk.Button(settings,text='Reset Settings',command=self.reset_settings).grid(row=r+2,column=0,columnspan=2,sticky='ew',pady=2)
        ttk.Label(editor,text='Timeline — drag clips to move; snapping applies automatically').pack(fill='x');holder=ttk.Frame(editor);holder.pack(fill='both',expand=True);self.timeline=tk.Canvas(holder,bg='#0b1220',highlightthickness=0,height=320);sx=ttk.Scrollbar(holder,orient='horizontal',command=self.timeline.xview);self.timeline.configure(xscrollcommand=sx.set);self.timeline.pack(fill='both',expand=True);sx.pack(fill='x');self.timeline.bind('<Configure>',lambda e:self.draw());self.timeline.bind('<Button-1>',self.press);self.timeline.bind('<B1-Motion>',self.drag_move);self.timeline.bind('<ButtonRelease-1>',lambda e:setattr(self,'drag',None))
        self.status=tk.StringVar(value='Settings start clean every launch. Add video clips to begin.');ttk.Label(self.window,textvariable=self.status).pack(fill='x',padx=8,pady=(0,7))
    def probe(self,path):
        try:
            raw=subprocess.check_output(['ffprobe','-v','quiet','-print_format','json','-show_format',path],text=True);return float(json.loads(raw)['format']['duration'])
        except Exception:return 10.
    def add_clips(self):
        paths=filedialog.askopenfilenames(filetypes=[('Videos','*.mp4 *.mov *.mkv *.avi *.webm *.m4v'),('All files','*.*')]);end=max((c.start+c.length() for c in self.clips),default=0)
        for path in paths:
            duration=self.probe(path);self.clips.append(Clip(path,duration,0,duration,end));end+=duration
        self.draw();self.status.set(f'{len(self.clips)} clip(s) in timeline.')
    def snap(self,value):
        text=self.v['snap'].get();unit={'1 frame':1/30,'0.1 second':.1,'0.5 second':.5,'1 second':1,'Off':0}[text];return value if not unit else round(value/unit)*unit
    def draw(self):
        c=self.timeline;c.delete('all');scale=50;h=max(200,c.winfo_height());end=max((x.start+x.length() for x in self.clips),default=20);w=max(c.winfo_width(),end*scale+100);c.configure(scrollregion=(0,0,w,h))
        for second in range(int(end)+3):c.create_line(second*scale,0,second*scale,h,fill='#475569' if second%5==0 else '#1e293b');c.create_text(second*scale+2,12,text=f'{second}s',fill='#94a3b8',anchor='nw')
        colors=('#2563eb','#7c3aed','#db2777','#ea580c','#16a34a','#0891b2')
        for i,clip in enumerate(self.clips):
            x=clip.start*scale;y=55+(i%5)*48;right=x+clip.length()*scale;c.create_rectangle(x,y,right,y+38,fill=colors[i%len(colors)],outline='#f97316' if i==self.selected else '#e5e7eb',width=3 if i==self.selected else 1,tags=(f'clip:{i}',));c.create_text(x+6,y+19,text=os.path.basename(clip.path),fill='white',anchor='w',tags=(f'clip:{i}',))
    def press(self,event):
        x=self.timeline.canvasx(event.x);y=self.timeline.canvasy(event.y)
        for item in reversed(self.timeline.find_overlapping(x,y,x,y)):
            for tag in self.timeline.gettags(item):
                if tag.startswith('clip:'):self.selected=int(tag.split(':')[1]);self.drag=(x-self.clips[self.selected].start*50);self.draw();return
    def drag_move(self,event):
        if self.selected is None or self.drag is None:return
        self.clips[self.selected].start=max(0,self.snap((self.timeline.canvasx(event.x)-self.drag)/50));self.draw()
    def cut_selected(self):
        if self.selected is None:return
        clip=self.clips[self.selected];at=float(self.v['cut'].get() or 0)
        if not 0<at<clip.length():messagebox.showwarning('Cut','Cut time must be inside the selected clip.');return
        second=Clip(clip.path,clip.duration,clip.source_in+at,clip.source_out,clip.start+at);clip.source_out=clip.source_in+at;self.clips.insert(self.selected+1,second);self.draw()
    def move_custom(self):
        if self.selected is not None:self.clips[self.selected].start=max(0,self.snap(float(self.v['custom_move'].get() or 0)));self.draw()
    def remove_clip(self):
        if self.selected is not None:self.clips.pop(self.selected);self.selected=None;self.draw()
    def clear_all(self):self.clips.clear();self.selected=None;self.reset_settings();self.draw()
    def reset_settings(self):
        values={'crop_x':'0','crop_y':'0','crop_w':'0','crop_h':'0','width':'1920','height':'1080','rotate':'0','zoom':'1.0','speed':'1.0','fade_in':'0','fade_out':'0','brightness':'0','contrast':'1.0','saturation':'1.0','hue':'0','filter':'None','cut':'0','snap':'1 second','custom_move':'0'}
        for k,v in values.items():self.v[k].set(v)
    def filters(self,duration):
        v=self.v;parts=[];cw=int(v['crop_w'].get());ch=int(v['crop_h'].get())
        if cw>0 and ch>0:parts.append(f"crop={cw}:{ch}:{int(v['crop_x'].get())}:{int(v['crop_y'].get())}")
        zoom=float(v['zoom'].get());width=max(2,int(int(v['width'].get())*zoom)//2*2);height=max(2,int(int(v['height'].get())*zoom)//2*2);parts.append(f'scale={width}:{height}')
        rotate=v['rotate'].get();parts+=({'90':['transpose=1'],'180':['hflip','vflip'],'270':['transpose=2']}.get(rotate,[]));parts.append(f"eq=brightness={float(v['brightness'].get())}:contrast={float(v['contrast'].get())}:saturation={float(v['saturation'].get())}")
        if float(v['hue'].get()):parts.append(f"hue=h={float(v['hue'].get())}")
        extra={'Grayscale':'hue=s=0','Sepia':'colorchannelmixer=.393:.769:.189:.349:.686:.168:.272:.534:.131','Vintage':'curves=vintage','Cool':'colorbalance=bs=.2','Warm':'colorbalance=rs=.2','Sharpen':'unsharp=5:5:1','Blur':'boxblur=2'}
        if v['filter'].get() in extra:parts.append(extra[v['filter'].get()])
        speed=float(v['speed'].get());parts.append(f'setpts=PTS/{speed}');fade_in=float(v['fade_in'].get());fade_out=float(v['fade_out'].get());
        if fade_in>0:parts.append(f'fade=t=in:st=0:d={fade_in}')
        if fade_out>0:parts.append(f'fade=t=out:st={max(0,duration/speed-fade_out)}:d={fade_out}')
        return ','.join(parts),speed
    def export_mp4(self):
        if not self.clips:messagebox.showwarning('Videos','Add clips first.');return
        path=filedialog.asksaveasfilename(defaultextension='.mp4',filetypes=[('MP4','*.mp4')]);
        if not path:return
        self.stop_event.clear();self.stop_button.config(state='normal')
        def work():
            try:
                with tempfile.TemporaryDirectory() as d:
                    pieces=[]
                    for i,clip in enumerate(sorted(self.clips,key=lambda x:x.start)):
                        if self.stop_event.is_set():raise RuntimeError('Export stopped.')
                        out=os.path.join(d,f'clip_{i:04d}.mp4');vf,speed=self.filters(clip.length());af=f'atempo={min(2,max(.5,speed))}'
                        cmd=['ffmpeg','-y','-ss',str(clip.source_in),'-t',str(clip.length()),'-i',clip.path,'-vf',vf,'-af',af,'-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',out];self.process=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);self.process.wait()
                        if self.process.returncode:raise RuntimeError('FFmpeg could not process a clip. Verify settings and FFmpeg installation.')
                        pieces.append(out);self.window.after(0,lambda n=i+1:self.status.set(f'Processed clip {n} of {len(self.clips)}'))
                    listing=os.path.join(d,'concat.txt')
                    with open(listing,'w',encoding='utf-8') as f:
                        for p in pieces:f.write("file '"+p.replace("'","'\\''")+"'\n")
                    self.process=subprocess.Popen(['ffmpeg','-y','-f','concat','-safe','0','-i',listing,'-c','copy',path],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);self.process.wait()
                    if self.process.returncode:raise RuntimeError('FFmpeg could not assemble the final MP4.')
                self.window.after(0,lambda:self.status.set(f'Exported {path}'))
            except Exception as e:self.window.after(0,lambda e=e:messagebox.showerror('Video export',str(e)))
            self.window.after(0,lambda:self.stop_button.config(state='disabled'))
        threading.Thread(target=work,daemon=True).start()
    def stop(self):
        self.stop_event.set()
        if self.process and self.process.poll() is None:self.process.terminate()
    def back(self):
        self.stop()
        if self.on_back:self.on_back(self)

def open_video_tool(parent,on_back=None):return VideoTool(parent,on_back)
