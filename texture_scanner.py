"""Embedded automatic and configurable raw-texture tool for AI Generator."""
import bz2, gzip, io, lzma, os, struct, threading, tkinter as tk, zlib
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk

SIGNATURES={'PNG':b'\x89PNG\r\n\x1a\n','JPEG':b'\xff\xd8\xff','DDS':b'DDS ','BMP':b'BM','KTX':b'\xabKTX 11\xbb\r\n\x1a\n','KTX2':b'\xabKTX 20\xbb\r\n\x1a\n','PVR':b'PVR\x03'}
EXTENSIONS={'PNG':'.png','JPEG':'.jpg','DDS':'.dds','BMP':'.bmp','KTX':'.ktx','KTX2':'.ktx2','PVR':'.pvr'}
FORMATS=('RGBA8888','BGRA8888','ARGB8888','ABGR8888','RGB888','BGR888','RGB565','BGR565','RGBA5551','ARGB1555','RGBA4444','ARGB4444','L8 Grayscale','A8 Alpha','LA88','Indexed 8-bit','Indexed 4-bit','DXT1 / BC1','DXT3 / BC2','DXT5 / BC3','ATI1 / BC4','ATI2 / BC5')
PALETTES=('RGBA8888','BGRA8888','ARGB8888','ABGR8888','RGB565','BGR565','RGBA5551','ARGB1555','RGBA4444','ARGB4444')
SWIZZLES=('Linear','Morton / Z-order','Tiled 4x4','Tiled 8x8','Tiled 16x16','PS2 GS 8x8','Wii 4x4 / CMPR','GameCube 4x4','Xbox 360 tiled (experimental)')
COMPRESSIONS=('None','Auto detect','ZLIB','Raw DEFLATE','GZIP','BZIP2','LZMA / XZ')

def size_text(n):
    n=float(max(0,n))
    for u in ('B','KB','MB','GB'):
        if n<1024 or u=='GB': return f'{n:.0f} {u}' if u=='B' else f'{n:.1f} {u}'
        n/=1024
def integer(v,name,minimum=0):
    try:n=int(str(v).strip(),0)
    except ValueError as e:raise ValueError(f'{name} must be decimal or 0x hexadecimal.') from e
    if n<minimum:raise ValueError(f'{name} must be at least {minimum}.')
    return n

@dataclass
class TextureResult:
    kind:str;offset:int;size:int;width:int=0;height:int=0
    def label(self,n):return f'Texture {n:03d} | {self.kind} | 0x{self.offset:08X} | {self.width or "?"}×{self.height or "?"} | {size_text(self.size)}'

class TextureScanner:
    def __init__(self,parent,on_back=None):
        self.on_back=on_back;self.window=ttk.Frame(parent,style='App.TFrame');self.window.pack(fill='both',expand=True)
        self.data=b'';self.path='';self.results=[];self.scanning=False;self.stop_event=threading.Event();self.preview_image=None;self.preview_photo=None;self.zoom=1.;self.pan=[0,0];self.drag=None
        self._build_ui()
    def _build_ui(self):
        bar=ttk.Frame(self.window,padding=(10,8,10,6));bar.pack(fill='x')
        ttk.Button(bar,text='← Back to Home',command=self.request_back).pack(side='left',padx=(0,8))
        self.path_var=tk.StringVar();ttk.Entry(bar,textvariable=self.path_var).pack(side='left',fill='x',expand=True)
        ttk.Button(bar,text='Open Any File',command=self.open_file).pack(side='left',padx=6)
        self.scan_button=ttk.Button(bar,text='Search Textures',command=self.start_scan);self.scan_button.pack(side='left')
        self.stop_button=ttk.Button(bar,text='Stop Scan',command=self.stop_scan,state='disabled');self.stop_button.pack(side='left',padx=(6,0))
        row=ttk.Frame(self.window,padding=(10,0,10,6));row.pack(fill='x');self.progress=tk.DoubleVar();self.progress_text=tk.StringVar(value='0%');self.results_text=tk.StringVar(value='Results: 0')
        ttk.Progressbar(row,variable=self.progress,maximum=100,style='Accent.Horizontal.TProgressbar').pack(side='left',fill='x',expand=True)
        ttk.Label(row,textvariable=self.progress_text,width=6).pack(side='left',padx=6);ttk.Label(row,textvariable=self.results_text,width=16).pack(side='left')
        pane=ttk.Panedwindow(self.window,orient='horizontal');pane.pack(fill='both',expand=True,padx=10,pady=(0,6));left=ttk.Frame(pane);right=ttk.Frame(pane);pane.add(left,weight=0);pane.add(right,weight=1)
        tabs=ttk.Notebook(left);tabs.pack(fill='both',expand=True);det=ttk.Frame(tabs,padding=6);raw=ttk.Frame(tabs,padding=6);tabs.add(det,text='Detected');tabs.add(raw,text='Raw Settings');self.raw_tab=raw
        self._detected_ui(det);self._raw_ui(raw)
        pbar=ttk.Frame(right);pbar.pack(fill='x');ttk.Label(pbar,text='Preview').pack(side='left');self.zoom_text=tk.StringVar(value='100%');ttk.Label(pbar,textvariable=self.zoom_text,width=7).pack(side='right');ttk.Button(pbar,text='Fit',command=self.fit).pack(side='right',padx=4);ttk.Button(pbar,text='100%',command=self.actual).pack(side='right')
        self.canvas=tk.Canvas(right,bg='#020617',highlightthickness=0,cursor='fleur');self.canvas.pack(fill='both',expand=True);self.canvas.bind('<MouseWheel>',self.wheel);self.canvas.bind('<ButtonPress-1>',self.pan_start);self.canvas.bind('<B1-Motion>',self.pan_move);self.canvas.bind('<Configure>',lambda e:self.draw())
        ex=ttk.Frame(right,padding=(0,6,0,0));ex.pack(fill='x');ttk.Label(ex,text='Export preview:').pack(side='left')
        for text,ext in [('PNG','.png'),('JPG','.jpg'),('DDS','.dds'),('TGA','.tga')]:ttk.Button(ex,text=text,command=lambda x=ext:self.export_preview(x)).pack(side='left',padx=(6,0))
        self.status=tk.StringVar(value='Open a file, scan containers, or use Raw Settings.');ttk.Label(self.window,textvariable=self.status).pack(fill='x',padx=10,pady=(0,8))
    def _detected_ui(self,p):
        f=ttk.Frame(p);f.pack(fill='both',expand=True);self.result_list=tk.Listbox(f,width=52,height=18,bg='#0f172a',fg='white',exportselection=False);sy=ttk.Scrollbar(f,orient='vertical',command=self.result_list.yview);sx=ttk.Scrollbar(f,orient='horizontal',command=self.result_list.xview);self.result_list.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);self.result_list.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew');f.rowconfigure(0,weight=1);f.columnconfigure(0,weight=1);self.result_list.bind('<<ListboxSelect>>',self.preview_selected)
        b=ttk.Frame(p);b.pack(fill='x',pady=(6,0));ttk.Button(b,text='Extract Original',command=self.extract_selected).pack(side='left',fill='x',expand=True);ttk.Button(b,text='Export All',command=self.export_all_detected).pack(side='left',fill='x',expand=True,padx=4);ttk.Button(b,text='Use as Raw',command=self.use_as_raw).pack(side='left',fill='x',expand=True)
    def _raw_ui(self,p):
        self.v={k:tk.StringVar(value=v) for k,v in {'width':'256','height':'256','offset':'0x0','stride':'0','format':'RGBA8888','endian':'Little','swizzle':'Linear','compression':'None','compressed_size':'0','palette_offset':'0x0','palette_format':'RGBA8888','palette_entries':'256','alpha':'Straight','count':'1','texture_stride':'0'}.items()}
        rows=[('Width','width',None),('Height','height',None),('Data offset','offset',None),('Row stride (0=auto)','stride',None),('Format','format',FORMATS),('Endian','endian',('Little','Big')),('Swizzle','swizzle',SWIZZLES),('Compression','compression',COMPRESSIONS),('Compressed size (0=rest)','compressed_size',None),('Palette offset','palette_offset',None),('Palette format','palette_format',PALETTES),('Palette entries','palette_entries',('16','256')),('Alpha','alpha',('Straight','Premultiplied','Opaque')),('Texture count','count',None),('Texture stride (0=auto)','texture_stride',None)]
        for r,(label,key,values) in enumerate(rows):
            ttk.Label(p,text=label).grid(row=r,column=0,sticky='w',pady=1);w=ttk.Combobox(p,textvariable=self.v[key],values=values,state='readonly',width=28) if values else ttk.Entry(p,textvariable=self.v[key],width=30);w.grid(row=r,column=1,sticky='ew',padx=(7,0),pady=1)
        p.columnconfigure(1,weight=1);r=len(rows);ttk.Button(p,text='Decode / Preview',command=self.decode_raw).grid(row=r,column=0,columnspan=2,sticky='ew',pady=(6,2));ttk.Button(p,text='Export All Raw Textures',command=self.export_all_raw).grid(row=r+1,column=0,columnspan=2,sticky='ew',pady=2);ttk.Label(p,text='Offsets accept decimal or 0x hex. Console layouts can be game-specific.',wraplength=370).grid(row=r+2,column=0,columnspan=2,sticky='w',pady=(4,0))
    def open_file(self):
        path=filedialog.askopenfilename(title='Select any file',filetypes=[('All files','*.*')])
        if not path:return
        try:
            with open(path,'rb') as f:self.data=f.read()
            self.path=path;self.path_var.set(path);self.status.set(f'Loaded {size_text(len(self.data))}.')
        except Exception as e:messagebox.showerror('Open texture source',str(e))
    def start_scan(self):
        if not self.data:self.open_file()
        if not self.data or self.scanning:return
        self.scanning=True;self.stop_event.clear();self.scan_button.config(state='disabled');self.stop_button.config(state='normal');self.set_progress(0,0);threading.Thread(target=self.scan_worker,daemon=True).start()
    def stop_scan(self):self.stop_event.set();self.stop_button.config(state='disabled');self.status.set('Stopping; keeping results found so far…')
    def scan_worker(self):
        found=[]
        for num,(kind,sig) in enumerate(SIGNATURES.items(),1):
            pos=0
            while not self.stop_event.is_set():
                pos=self.data.find(sig,pos)
                if pos<0:break
                x=self.measure(kind,pos)
                if x:found.append(x)
                pos+=len(sig)
            self.window.after(0,lambda p=num/len(SIGNATURES)*100,n=len(found):self.set_progress(p,n))
            if self.stop_event.is_set():break
        seen={};[seen.setdefault((x.offset,x.kind),x) for x in found];results=sorted(seen.values(),key=lambda x:x.offset);stopped=self.stop_event.is_set();self.window.after(0,lambda:self.finish(results,stopped))
    def measure(self,kind,o):
        try:
            if kind=='PNG':w,h=struct.unpack_from('>II',self.data,o+16);end=self.data.find(b'IEND',o+24);s=end+8-o if end>=0 else len(self.data)-o
            elif kind=='JPEG':w=h=0;end=self.data.find(b'\xff\xd9',o+3);s=end+2-o if end>=0 else len(self.data)-o
            elif kind=='BMP':s=struct.unpack_from('<I',self.data,o+2)[0];w,h=map(abs,struct.unpack_from('<ii',self.data,o+18))
            elif kind=='DDS':h,w=struct.unpack_from('<II',self.data,o+12);s=self.next_sig(o+4)-o
            elif kind=='KTX':w,h=struct.unpack_from('<II',self.data,o+36);s=self.next_sig(o+12)-o
            elif kind=='KTX2':w,h=struct.unpack_from('<II',self.data,o+20);s=self.next_sig(o+12)-o
            else:h,w=struct.unpack_from('<II',self.data,o+24);s=self.next_sig(o+4)-o
            if w>262144 or h>262144:w=h=0
            return TextureResult(kind,o,min(max(0,s),len(self.data)-o),w,h)
        except:return None
    def next_sig(self,start):
        x=[self.data.find(s,start) for s in SIGNATURES.values()];x=[n for n in x if n>=0];return min(x) if x else len(self.data)
    def set_progress(self,p,n):self.progress.set(p);self.progress_text.set(f'{p:.0f}%');self.results_text.set(f'Results: {n:,}')
    def finish(self,results,stopped):
        self.scanning=False;self.scan_button.config(state='normal');self.stop_button.config(state='disabled');self.results=results;self.result_list.delete(0,'end')
        for n,x in enumerate(results,1):self.result_list.insert('end',x.label(n))
        self.set_progress(100 if not stopped else self.progress.get(),len(results));self.status.set(f'{"Stopped; kept" if stopped else "Search complete:"} {len(results)} textures.')
        if results:self.result_list.selection_set(0);self.preview_selected()
    def preview_selected(self,e=None):
        s=self.result_list.curselection()
        if not s:return
        x=self.results[s[0]]
        try:
            from PIL import Image
            with Image.open(io.BytesIO(self.data[x.offset:x.offset+x.size])) as im:self.set_image(im.convert('RGBA'))
        except Exception:self.preview_image=None;self.canvas.delete('all');self.canvas.create_text(self.canvas.winfo_width()/2,self.canvas.winfo_height()/2,text=f'{x.kind} {x.width}×{x.height}\nSelect Use as Raw to decode manually.',fill='white',justify='center')
    def use_as_raw(self):
        s=self.result_list.curselection()
        if not s:return
        x=self.results[s[0]];self.v['offset'].set(hex(x.offset));self.v['width'].set(str(x.width or 256));self.v['height'].set(str(x.height or 256));self.status.set('Detected values copied. Choose Raw Settings and set the pixel format.')
    def decompress(self,payload,mode):
        if mode=='None':return payload
        funcs={'ZLIB':lambda b:zlib.decompress(b),'Raw DEFLATE':lambda b:zlib.decompress(b,-15),'GZIP':gzip.decompress,'BZIP2':bz2.decompress,'LZMA / XZ':lzma.decompress}
        if mode!='Auto detect':return funcs[mode](payload)
        for f in (gzip.decompress,bz2.decompress,lzma.decompress,lambda b:zlib.decompress(b),lambda b:zlib.decompress(b,-15)):
            try:return f(payload)
            except:pass
        raise ValueError('Compression could not be detected.')
    def bpp(self,f):return 4 if '8888' in f else 3 if f in ('RGB888','BGR888') else 2 if f in ('RGB565','BGR565','RGBA5551','ARGB1555','RGBA4444','ARGB4444','LA88') else 1
    def untile(self,raw,w,h,unit,mode):
        if mode=='Linear':return raw
        tile=4 if ('4x4' in mode or 'GameCube' in mode or 'Wii' in mode) else 8 if ('8x8' in mode or 'PS2' in mode) else 16 if '16x16' in mode else 32 if 'Xbox' in mode else 0;out=bytearray(w*h*unit)
        if not tile:
            def compact(v):v&=0x55555555;v=(v^(v>>1))&0x33333333;v=(v^(v>>2))&0x0f0f0f0f;v=(v^(v>>4))&0x00ff00ff;return (v^(v>>8))&0xffff
            for i in range(w*h):
                x,y=compact(i),compact(i>>1)
                if x<w and y<h:out[(y*w+x)*unit:(y*w+x+1)*unit]=raw[i*unit:(i+1)*unit]
            return bytes(out)
        src=0
        for ty in range(0,h,tile):
            for tx in range(0,w,tile):
                for y in range(tile):
                    for x in range(tile):
                        if tx+x<w and ty+y<h and src+unit<=len(raw):d=((ty+y)*w+tx+x)*unit;out[d:d+unit]=raw[src:src+unit]
                        src+=unit
        return bytes(out)
    def dds(self,raw,w,h,cc):
        unit=8 if cc in (b'DXT1',b'ATI1') else 16;linear=((w+3)//4)*((h+3)//4)*unit
        return b'DDS '+struct.pack('<7I11I',124,0xA1007,h,w,linear,0,1,*([0]*11))+struct.pack('<II4s5I',32,4,cc,0,0,0,0,0)+struct.pack('<5I',0x1000,0,0,0,0)+raw
    def color(self,b,f,endian):
        b=b.ljust(self.bpp(f),b'\0')
        maps={'RGBA8888':(0,1,2,3),'BGRA8888':(2,1,0,3),'ARGB8888':(1,2,3,0),'ABGR8888':(3,2,1,0)}
        if f in maps:return tuple(b[i] for i in maps[f])
        if f=='RGB888':return (*b[:3],255)
        if f=='BGR888':return (b[2],b[1],b[0],255)
        if f=='L8 Grayscale':return (b[0],b[0],b[0],255)
        if f=='A8 Alpha':return (255,255,255,b[0])
        if f=='LA88':return (b[0],b[0],b[0],b[1])
        n=int.from_bytes(b[:2],endian)
        if f in ('RGB565','BGR565'):
            c=(((n>>11)&31)*255//31,((n>>5)&63)*255//63,(n&31)*255//31,255);return (c[2],c[1],c[0],255) if f=='BGR565' else c
        if f=='RGBA5551':return (((n>>11)&31)*255//31,((n>>6)&31)*255//31,((n>>1)&31)*255//31,255 if n&1 else 0)
        if f=='ARGB1555':return (((n>>10)&31)*255//31,((n>>5)&31)*255//31,(n&31)*255//31,255 if n&0x8000 else 0)
        q=[((n>>s)&15)*17 for s in (12,8,4,0)];return tuple(q if f=='RGBA4444' else (q[1],q[2],q[3],q[0]))
    def decode_one(self,index=0):
        from PIL import Image
        v=self.v;w=integer(v['width'].get(),'Width',1);h=integer(v['height'].get(),'Height',1);base=integer(v['offset'].get(),'Offset');fmt=v['format'].get();end='little' if v['endian'].get()=='Little' else 'big';stride=integer(v['texture_stride'].get(),'Texture stride')
        if not stride and v['compression'].get()=='None':
            if fmt.startswith(('DXT','ATI')):stride=((w+3)//4)*((h+3)//4)*(8 if fmt in ('DXT1 / BC1','ATI1 / BC4') else 16)
            elif fmt=='Indexed 4-bit':stride=(w*h+1)//2
            elif fmt=='Indexed 8-bit':stride=w*h
            else:stride=(integer(v['stride'].get(),'Row stride') or w*self.bpp(fmt))*h
        if index and not stride:raise ValueError('Set Texture stride for multiple compressed textures.')
        offset=base+index*stride
        cs=integer(v['compressed_size'].get(),'Compressed size');source=self.data[offset:offset+cs] if cs else self.data[offset:];raw=self.decompress(source,v['compression'].get())
        if fmt.startswith(('DXT','ATI')):
            cc={'DXT1 / BC1':b'DXT1','DXT3 / BC2':b'DXT3','DXT5 / BC3':b'DXT5','ATI1 / BC4':b'ATI1','ATI2 / BC5':b'ATI2'}[fmt];unit=8 if cc in (b'DXT1',b'ATI1') else 16;bw,bh=(w+3)//4,(h+3)//4;raw=self.untile(raw[:bw*bh*unit],bw,bh,unit,v['swizzle'].get());im=Image.open(io.BytesIO(self.dds(raw,w,h,cc))).convert('RGBA')
        elif fmt.startswith('Indexed'):
            count=16 if '4-bit' in fmt else 256;pf=v['palette_format'].get();ps=self.bpp(pf);po=integer(v['palette_offset'].get(),'Palette offset');pal=[self.color(self.data[po+i*ps:po+(i+1)*ps],pf,end) for i in range(min(count,integer(v['palette_entries'].get(),'Palette entries',1)))];idx=[]
            if count==16:
                for x in raw[:(w*h+1)//2]:idx.extend((x>>4,x&15))
            else:idx=list(raw[:w*h])
            im=Image.new('RGBA',(w,h));im.putdata([pal[x%len(pal)] for x in idx[:w*h]])
        else:
            ps=self.bpp(fmt);row=integer(v['stride'].get(),'Row stride') or w*ps;packed=b''.join(raw[y*row:y*row+w*ps] for y in range(h));packed=self.untile(packed,w,h,ps,v['swizzle'].get());px=[self.color(packed[i:i+ps],fmt,end) for i in range(0,min(len(packed),w*h*ps),ps)];im=Image.new('RGBA',(w,h));im.putdata(px+[(0,0,0,0)]*(w*h-len(px)))
        if v['alpha'].get()=='Opaque':im.putalpha(255)
        return im
    def decode_raw(self):
        try:self.set_image(self.decode_one());self.status.set('Raw texture decompressed/decoded for preview.')
        except Exception as e:messagebox.showerror('Decode raw texture',str(e))
    def set_image(self,im):self.preview_image=im.copy();self.fit()
    def fit(self):
        if not self.preview_image:return
        self.zoom=min((max(1,self.canvas.winfo_width()-20))/self.preview_image.width,(max(1,self.canvas.winfo_height()-20))/self.preview_image.height,8);self.pan=[0,0];self.draw()
    def actual(self):self.zoom=1;self.pan=[0,0];self.draw()
    def draw(self):
        if not self.preview_image:return
        from PIL import Image,ImageTk
        w,h=max(1,int(self.preview_image.width*self.zoom)),max(1,int(self.preview_image.height*self.zoom));im=self.preview_image.resize((w,h),getattr(Image,'Resampling',Image).NEAREST if self.zoom>=2 else getattr(Image,'Resampling',Image).LANCZOS);self.preview_photo=ImageTk.PhotoImage(im);self.canvas.delete('all');self.canvas.create_image(self.canvas.winfo_width()/2+self.pan[0],self.canvas.winfo_height()/2+self.pan[1],image=self.preview_photo);self.zoom_text.set(f'{self.zoom*100:.0f}%')
    def wheel(self,e):self.zoom=max(.05,min(32,self.zoom*(1.2 if e.delta>0 else 1/1.2)));self.draw();return 'break'
    def pan_start(self,e):self.drag=(e.x,e.y,*self.pan)
    def pan_move(self,e):
        if self.drag:x,y,px,py=self.drag;self.pan=[px+e.x-x,py+e.y-y];self.draw()
    def save_image(self,im,path):im.convert('RGB').save(path) if path.lower().endswith(('.jpg','.jpeg')) else im.save(path)
    def export_preview(self,ext):
        if not self.preview_image:messagebox.showwarning('Export','Preview a texture first.');return
        p=filedialog.asksaveasfilename(defaultextension=ext,filetypes=[(ext[1:].upper(),'*'+ext)])
        if p:
            try:self.save_image(self.preview_image,p);self.status.set(f'Exported {p}')
            except Exception as e:messagebox.showerror('Export',str(e))
    def extract_selected(self):
        s=self.result_list.curselection()
        if not s:return
        x=self.results[s[0]];p=filedialog.asksaveasfilename(defaultextension=EXTENSIONS[x.kind])
        if p:
            with open(p,'wb') as f:f.write(self.data[x.offset:x.offset+x.size])
    def export_all_detected(self):
        if not self.results:messagebox.showwarning('Export All','No detected textures.');return
        folder=filedialog.askdirectory(title='Export all textures');
        if not folder:return
        self.stop_event.clear();self.stop_button.config(state='normal');count=0
        from PIL import Image
        for n,x in enumerate(self.results,1):
            if self.stop_event.is_set():break
            try:
                with Image.open(io.BytesIO(self.data[x.offset:x.offset+x.size])) as im:self.save_image(im.convert('RGBA'),os.path.join(folder,f'texture_{n:04d}.png'));count+=1
            except:pass
            self.set_progress(n/len(self.results)*100,count);self.window.update_idletasks()
        self.stop_button.config(state='disabled');self.status.set(f'Exported {count} decoded textures as PNG.')
    def export_all_raw(self):
        if not self.data:return
        folder=filedialog.askdirectory(title='Export all raw textures');
        if not folder:return
        count=integer(self.v['count'].get(),'Texture count',1);ext=filedialog.asksaveasfilename(title='Choose format/name',initialfile='texture.png',defaultextension='.png',filetypes=[('PNG','*.png'),('JPG','*.jpg'),('DDS','*.dds'),('TGA','*.tga')]);
        if not ext:return
        suffix=os.path.splitext(ext)[1].lower();stem=os.path.splitext(os.path.basename(ext))[0];self.stop_event.clear();self.stop_button.config(state='normal');done=0
        try:
            for i in range(count):
                if self.stop_event.is_set():break
                self.save_image(self.decode_one(i),os.path.join(folder,f'{stem}_{i+1:04d}{suffix}'));done+=1;self.set_progress((i+1)/count*100,done);self.window.update_idletasks()
            self.status.set(f'Exported {done} decompressed raw textures.')
        except Exception as e:messagebox.showerror('Export All Raw',str(e))
        self.stop_button.config(state='disabled')
    def request_back(self):
        if self.scanning:self.stop_scan();self.window.after(75,self.request_back);return
        if self.on_back:self.on_back(self)

def open_texture_scanner(parent,on_back=None):return TextureScanner(parent,on_back)
