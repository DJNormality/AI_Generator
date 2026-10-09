"""Embedded RGB channel compositor for AI Generator's Textures tab."""
import os, shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


CHANNELS = ('Red', 'Green', 'Blue', 'Alpha', 'Luminance')
PRESETS = {
    'Custom RGB': ('Red', 'Green', 'Blue'),
    'RMA — Roughness / Metallic / AO': ('Red', 'Green', 'Blue'),
    'ART — AO / Roughness / Translucency': ('Red', 'Green', 'Blue'),
    'CSM — Cavity / Specular / Mask': ('Red', 'Green', 'Blue'),
    'MK1 ID + Tone workflow': ('Blue', 'Green', 'Blue'),
}


def compose_channels(images, selectors, invert=(False, False, False), strengths=(1, 1, 1), size=None):
    """Build an RGB image from three PIL images; kept separate for testing."""
    from PIL import Image, ImageOps
    present = [image for image in images if image is not None]
    if not present:
        raise ValueError('Import at least one channel image.')
    target = size or present[0].size
    output = []
    for index in range(3):
        source = images[index] or present[0]
        source = source.convert('RGBA').resize(target, Image.Resampling.LANCZOS)
        name = selectors[index]
        if name == 'Luminance':
            channel = ImageOps.grayscale(source)
        else:
            channel = source.getchannel({'Red':'R','Green':'G','Blue':'B','Alpha':'A'}[name])
        if invert[index]:
            channel = ImageOps.invert(channel)
        factor = max(0.0, min(2.0, float(strengths[index])))
        if factor != 1:
            channel = channel.point(lambda value, f=factor: max(0, min(255, round(value * f))))
        output.append(channel)
    return Image.merge('RGB', output)


class RGBMixer:
    def __init__(self, parent):
        self.window = ttk.Frame(parent, style='App.TFrame')
        self.window.pack(fill='both', expand=True)
        self.images = [None, None, None]
        self.paths = [tk.StringVar(), tk.StringVar(), tk.StringVar()]
        self.selectors = [tk.StringVar(value=value) for value in ('Red','Green','Blue')]
        self.invert = [tk.BooleanVar(value=False) for _ in range(3)]
        self.strength = [tk.DoubleVar(value=100) for _ in range(3)]
        self.preview = None
        self.photo = None
        self.zoom = 1.0
        self.pan = [0, 0]
        self.drag = None
        self._build()

    def _build(self):
        top = ttk.Frame(self.window, padding=10); top.pack(fill='x')
        ttk.Label(top, text='RGB Channel Mixer', style='Section.TLabel').pack(side='left')
        ttk.Label(top, text='Combine packed material maps or recolor channel-based textures.').pack(side='left', padx=12)
        body = ttk.Panedwindow(self.window, orient='horizontal'); body.pack(fill='both', expand=True, padx=10, pady=(0,10))
        controls = ttk.Frame(body, padding=8); viewer = ttk.Frame(body); body.add(controls, weight=0); body.add(viewer, weight=1)
        self.preset = tk.StringVar(value='Custom RGB')
        ttk.Label(controls, text='Material preset').grid(row=0,column=0,sticky='w')
        preset = ttk.Combobox(controls,textvariable=self.preset,values=list(PRESETS),state='readonly',width=31)
        preset.grid(row=0,column=1,columnspan=3,sticky='ew',padx=(8,0)); preset.bind('<<ComboboxSelected>>',self.apply_preset)
        self.channel_labels=[]
        for index, color in enumerate(('R','G','B')):
            row=index+1
            label=ttk.Label(controls,text=f'{color} output'); label.grid(row=row,column=0,sticky='w',pady=5); self.channel_labels.append(label)
            ttk.Button(controls,text='Import',command=lambda i=index:self.import_image(i)).grid(row=row,column=1,padx=(8,4))
            ttk.Combobox(controls,textvariable=self.selectors[index],values=CHANNELS,state='readonly',width=11).grid(row=row,column=2)
            ttk.Checkbutton(controls,text='Invert',variable=self.invert[index],command=self.mix).grid(row=row,column=3,padx=5)
            ttk.Scale(controls,from_=0,to=200,variable=self.strength[index],command=lambda _v:self.mix()).grid(row=row+3,column=1,columnspan=2,sticky='ew',padx=(8,4))
            value=ttk.Label(controls,textvariable=self.paths[index],wraplength=320); value.grid(row=row+6,column=0,columnspan=4,sticky='w',pady=(0,4))
        # The staggered path rows above intentionally keep channel controls compact.
        actions=ttk.Frame(controls); actions.grid(row=10,column=0,columnspan=4,sticky='ew',pady=(8,0))
        ttk.Button(actions,text='Mix / Refresh',command=self.mix).pack(side='left',fill='x',expand=True)
        ttk.Button(actions,text='Clear',command=self.clear).pack(side='left',fill='x',expand=True,padx=5)
        ttk.Button(actions,text='Export Result',command=self.export).pack(side='left',fill='x',expand=True)
        ttk.Button(controls,text='Save Blender Node Functions',command=self.export_blender_nodes).grid(row=12,column=0,columnspan=4,sticky='ew',pady=(7,0))
        ttk.Label(controls,text='MK reference presets: RMA = roughness, metallic, AO; ART = AO, roughness, translucency. Each output can read any source channel.',wraplength=360).grid(row=11,column=0,columnspan=4,sticky='w',pady=(10,0))
        controls.columnconfigure(2,weight=1)
        bar=ttk.Frame(viewer); bar.pack(fill='x'); ttk.Label(bar,text='Final Result').pack(side='left')
        self.zoom_text=tk.StringVar(value='100%'); ttk.Label(bar,textvariable=self.zoom_text).pack(side='right'); ttk.Button(bar,text='Fit',command=self.fit).pack(side='right',padx=5)
        self.canvas=tk.Canvas(viewer,bg='#020617',highlightthickness=0,cursor='fleur'); self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<MouseWheel>',self.wheel); self.canvas.bind('<ButtonPress-1>',self.pan_start); self.canvas.bind('<B1-Motion>',self.pan_move); self.canvas.bind('<Configure>',lambda _e:self.draw())
        self.status=tk.StringVar(value='Import separate maps or reuse one packed RGB texture in all three slots.')
        ttk.Label(self.window,textvariable=self.status).pack(fill='x',padx=10,pady=(0,8))

    def apply_preset(self, _event=None):
        values=PRESETS[self.preset.get()]
        for variable,value in zip(self.selectors,values): variable.set(value)
        labels={
            'RMA — Roughness / Metallic / AO':('R · Roughness','G · Metallic','B · Ambient occlusion'),
            'ART — AO / Roughness / Translucency':('R · Ambient occlusion','G · Roughness','B · Translucency'),
            'CSM — Cavity / Specular / Mask':('R · Cavity','G · Specular','B · Mask'),
            'MK1 ID + Tone workflow':('R · ID blue extraction','G · Tone green extraction','B · Tone blue dirt/damage'),
        }.get(self.preset.get(),('R output','G output','B output'))
        for widget,text in zip(self.channel_labels,labels): widget.configure(text=text)
        self.mix()

    def import_image(self,index):
        path=filedialog.askopenfilename(title=f'Import {"RGB"[index]} channel source',filetypes=[('Images','*.png *.jpg *.jpeg *.bmp *.tga *.tif *.tiff *.dds *.webp'),('All files','*.*')])
        if not path:return
        try:
            from PIL import Image
            image=Image.open(path); image.load(); self.images[index]=image.convert('RGBA'); self.paths[index].set(os.path.basename(path)); self.mix()
        except Exception as error:messagebox.showerror('Import channel',str(error))

    def mix(self):
        if not any(self.images):return
        try:
            strengths=[value.get()/100 for value in self.strength]
            self.preview=compose_channels(self.images,[value.get() for value in self.selectors],[value.get() for value in self.invert],strengths)
            self.fit(); self.status.set(f'Mixed final RGB result at {self.preview.width} × {self.preview.height}.')
        except Exception as error:self.status.set(str(error))

    def clear(self):
        self.images=[None,None,None]; self.preview=None
        for path in self.paths:path.set('')
        self.canvas.delete('all'); self.status.set('RGB mixer cleared.')

    def export(self):
        if self.preview is None:messagebox.showwarning('Export Result','Mix a result first.');return
        path=filedialog.asksaveasfilename(defaultextension='.png',filetypes=[('PNG','*.png'),('TGA','*.tga'),('TIFF','*.tif'),('BMP','*.bmp')])
        if path:
            try:self.preview.save(path);self.status.set(f'Exported {path}')
            except Exception as error:messagebox.showerror('Export Result',str(error))

    def export_blender_nodes(self):
        source=os.path.join(os.path.dirname(os.path.abspath(__file__)),'blender_texture_nodes.py')
        target=filedialog.asksaveasfilename(title='Save Blender node functions',initialfile='blender_texture_nodes.py',defaultextension='.py',filetypes=[('Python','*.py')])
        if target:
            try:shutil.copy2(source,target);self.status.set(f'Saved Blender node functions to {target}.')
            except Exception as error:messagebox.showerror('Save Blender Nodes',str(error))

    def fit(self):
        if self.preview is None:return
        self.zoom=min(max(1,self.canvas.winfo_width()-20)/self.preview.width,max(1,self.canvas.winfo_height()-20)/self.preview.height,8);self.pan=[0,0];self.draw()
    def draw(self):
        if self.preview is None:return
        from PIL import Image,ImageTk
        size=(max(1,round(self.preview.width*self.zoom)),max(1,round(self.preview.height*self.zoom)))
        image=self.preview.resize(size,Image.Resampling.NEAREST if self.zoom>=2 else Image.Resampling.LANCZOS);self.photo=ImageTk.PhotoImage(image)
        self.canvas.delete('all');self.canvas.create_image(self.canvas.winfo_width()/2+self.pan[0],self.canvas.winfo_height()/2+self.pan[1],image=self.photo);self.zoom_text.set(f'{self.zoom*100:.0f}%')
    def wheel(self,event):self.zoom=max(.05,min(32,self.zoom*(1.2 if event.delta>0 else 1/1.2)));self.draw();return 'break'
    def pan_start(self,event):self.drag=(event.x,event.y,*self.pan)
    def pan_move(self,event):
        if self.drag:
            x,y,px,py=self.drag;self.pan=[px+event.x-x,py+event.y-y];self.draw()


def build_rgb_mixer(parent):
    return RGBMixer(parent)
