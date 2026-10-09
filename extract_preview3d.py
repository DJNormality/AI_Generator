"""Lightweight 3D and animation validation viewport for Extract."""
import math, struct, tkinter as tk
from tkinter import ttk

class ExtractPreview3D:
    def __init__(self,parent,status):
        self.parent=parent;self.status=status;self.vertices=[];self.faces=[];self.yaw=.5;self.pitch=-.3;self.zoom=1.;self.pan=[0.,0.];self.drag=None;self.frame=0;self.frames=0;self.playing=False;self.paused=False;self.skip=tk.IntVar(value=1)
        bar=ttk.Frame(parent);bar.pack(fill='x');ttk.Button(bar,text='Fit',command=self.fit).pack(side='left');self.test_button=ttk.Button(bar,text='Test Animation',command=lambda:None);self.play_button=ttk.Button(bar,text='Play',command=self.play);self.pause_button=ttk.Button(bar,text='Pause',command=self.pause);self.stop_button=ttk.Button(bar,text='Stop',command=self.stop);ttk.Label(bar,text='Frame skip').pack(side='left',padx=(10,3));ttk.Spinbox(bar,from_=1,to=120,textvariable=self.skip,width=5).pack(side='left')
        self.canvas=tk.Canvas(parent,bg='#020617',highlightthickness=1,highlightbackground='#334155');self.canvas.pack(fill='both',expand=True,pady=(4,0));self.canvas.bind('<MouseWheel>',self.wheel);self.canvas.bind('<ButtonPress-1>',self.press);self.canvas.bind('<B1-Motion>',self.motion);self.canvas.bind('<ButtonRelease-1>',lambda _e:setattr(self,'drag',None));self.canvas.bind('<ButtonPress-2>',self.pan_start);self.canvas.bind('<B2-Motion>',self.pan_move);self.canvas.bind('<Configure>',lambda _e:self.draw())
    def enable_animation_controls(self,command):
        self.test_button.configure(command=command)
        for widget in (self.test_button,self.play_button,self.pause_button,self.stop_button):widget.pack(side='left',padx=(5,0))
    def load_payload(self,payload):
        vertices=[];faces=[]
        if payload.lstrip().startswith((b'v ',b'#')):
            for raw in payload.decode('utf-8','ignore').splitlines():
                parts=raw.split()
                try:
                    if parts and parts[0]=='v' and len(parts)>=4:vertices.append(tuple(map(float,parts[1:4])))
                    elif parts and parts[0]=='f' and len(parts)>=4:faces.append(tuple(int(value.split('/')[0])-1 for value in parts[1:]))
                except Exception:pass
        if len(vertices)<3:
            vertices=self._float_cloud(payload);faces=[(index,index+1,index+2) for index in range(0,len(vertices)-2,3)]
        self.vertices,self.faces=vertices,faces;self.fit();return len(vertices)>=3
    def _float_cloud(self,payload):
        result=[];data=payload[:min(len(payload),2*1024*1024)]
        for endian in ('<','>'):
            candidate=[]
            for offset in range(0,len(data)-11,12):
                try:values=struct.unpack_from(endian+'3f',data,offset)
                except Exception:continue
                if all(math.isfinite(value) and abs(value)<100000 for value in values) and any(abs(value)>1e-8 for value in values):candidate.append(values)
                if len(candidate)>=6000:break
            if len(candidate)>len(result):result=candidate
        return result
    def set_geometry(self,vertices,faces):self.vertices=list(vertices);self.faces=list(faces);self.fit()
    def test_animation(self,payload):
        if not self.vertices:return False,'No valid model is loaded. Select a model result first.'
        if len(payload)<16:return False,'Animation data is too small.'
        valid=0
        for offset in range(0,min(len(payload)-4,1024*1024),4):
            value=struct.unpack_from('<f',payload,offset)[0]
            if math.isfinite(value) and abs(value)<100000:valid+=1
        if valid<12:return False,'Animation data does not contain enough plausible transform values.'
        self.frames=max(2,min(10000,valid//12));self.frame=0;self.draw();return True,f'Animation test passed: approximately {self.frames:,} transform frames. Playback is a structural preview.'
    def play(self):
        if not self.frames:self.status('Test animation data first.');return
        self.playing=True;self.paused=False;self._tick()
    def pause(self):self.paused=not self.paused;self.status('Animation paused.' if self.paused else 'Animation resumed.')
    def stop(self):self.playing=False;self.paused=False;self.frame=0;self.draw();self.status('Animation stopped.')
    def _tick(self):
        if not self.playing:return
        if not self.paused:self.frame=(self.frame+max(1,self.skip.get()))%self.frames;self.draw()
        self.parent.after(33,self._tick)
    def fit(self):self.zoom=1.;self.pan=[0.,0.];self.draw()
    def wheel(self,event):self.zoom=max(.05,min(50,self.zoom*(1.2 if event.delta>0 else 1/1.2)));self.draw();return 'break'
    def press(self,event):self.drag=('rotate',event.x,event.y,self.yaw,self.pitch)
    def motion(self,event):
        if self.drag and self.drag[0]=='rotate':_,x,y,yaw,pitch=self.drag;self.yaw=yaw+(event.x-x)*.009;self.pitch=max(-1.5,min(1.5,pitch+(event.y-y)*.009));self.draw()
    def pan_start(self,event):self.drag=('pan',event.x,event.y,*self.pan)
    def pan_move(self,event):
        if self.drag and self.drag[0]=='pan':_,x,y,px,py=self.drag;self.pan=[px+event.x-x,py+event.y-y];self.draw()
    def _points(self):
        if not self.vertices:return []
        cy,sy=math.cos(self.yaw),math.sin(self.yaw);cp,sp=math.cos(self.pitch),math.sin(self.pitch);pulse=math.sin(self.frame*.12)*.035 if self.frames else 0.;points=[]
        for index,(x,y,z) in enumerate(self.vertices):
            if self.frames:y+=math.sin(index*.13+self.frame*.09)*pulse
            x,z=x*cy-z*sy,x*sy+z*cy;y,z=y*cp-z*sp,y*sp+z*cp;points.append((x,y,z))
        xs=[p[0] for p in points];ys=[p[1] for p in points];span=max(max(xs)-min(xs),max(ys)-min(ys),1e-8);w=max(2,self.canvas.winfo_width());h=max(2,self.canvas.winfo_height());scale=min(w,h)*.78/span*self.zoom;cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2;return [(w/2+(x-cx)*scale+self.pan[0],h/2-(y-cy)*scale+self.pan[1],z) for x,y,z in points]
    def draw(self):
        c=self.canvas;c.delete('all');points=self._points()
        if not points:c.create_text(20,20,text='Select a model candidate to preview',anchor='nw',fill='#cbd5e1');return
        for face in self.faces[:100000]:
            try:coords=[value for index in face for value in points[index][:2]]
            except Exception:continue
            if len(coords)>=6:c.create_polygon(*coords,fill='#123047',outline='#67e8f9')
        c.create_text(8,8,text=f'{len(self.vertices):,} vertices  •  frame {self.frame}/{self.frames or 0}',anchor='nw',fill='#f8fafc')
