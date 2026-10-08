"""Layered blueprint and UV layout editor embedded in AI Generator."""
import json, math, os, re, struct, tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk


TOOLS=('Select','Paint','Erase','Clone Stamp','Smudge','Blur','Sharpen','Square','Triangle','Circle','Oval','Electrical','Plumbing','Water','Insert')
INSERTS={
 'Doors':('Interior Door','Exterior Door','Double Door','French Door','Sliding Door','Pocket Door','Bi-fold Door','Door Frame','Cased Opening','Single Garage Door','Double Garage Door'),
 'Fireplaces':('Fireplace','Corner Fireplace','Double-sided Fireplace','Hearth','Chimney'),
 'Bath & plumbing':('Bathtub','Corner Bathtub','Shower','Corner Shower','Walk-in Shower','Toilet','Single Sink','Double Sink','Water Heater'),
 'Steps & railings':('Straight Steps','L-shaped Steps','U-shaped Steps','Spiral Steps','Ramp','Straight Railing','Corner Railing','Balcony Railing','Handrail'),
 'Windows':('Single Window','Double Window','Bay Window','Casement Window','Sliding Window','Skylight'),
 'Appliances':('Refrigerator','Stove','Oven','Dishwasher','Microwave','Washer','Dryer','Freezer'),
 'Furniture':('Sofa','Sectional Sofa','Chair','Dining Table','Coffee Table','Desk','Bookcase','Television','Bench'),
 'Lighting':('Ceiling Light','Lamp','Wall Light','Outlet','Switch'),
 'Bedding':('Twin Bed','Queen Bed','King Bed','Nightstand'),
 'Cabinetry':('Base Cabinet','Wall Cabinet','Tall Cabinet','Corner Cabinet','Vanity','Island','Countertop','Pantry'),
}
TEMPLATES=('Blank Blueprint','Room Blueprint','House Grid','Cube UV Cross','Cylinder UV','Sphere UV Grid')


class DesignTool:
    def __init__(self,parent):
        self.parent=parent;self.layers=[];self.next_id=1;self.active_tool=tk.StringVar(value='Select');self.template=tk.StringVar(value='Blank Blueprint');self.shape_w=tk.DoubleVar(value=120);self.shape_h=tk.DoubleVar(value=80);self.scale=tk.DoubleVar(value=1.0);self.stroke=tk.DoubleVar(value=3);self.color='#111827';self.grid=tk.IntVar(value=20);self.snap=tk.BooleanVar(value=True);self.insert_category=tk.StringVar(value='Furniture');self.insert_item=tk.StringVar(value='Sofa');self.uv_path=tk.StringVar();self.uv_mode=tk.StringVar(value='Wireframe');self.uv_layer_id=None;self.header_open=True;self.drag=None;self.temp_points=[];self.selected=None;self.photos={};self.info=tk.StringVar(value='X 0  |  Y 0  |  Width 0  |  Height 0  |  Distance 0');self.status=tk.StringVar(value='Choose a template or drawing tool.');self._build();self.new_template()
    def _build(self):
        self.parent.grid_columnconfigure(0,weight=1);self.parent.grid_rowconfigure(1,weight=1)
        self.header_shell=ttk.Frame(self.parent);self.header_shell.grid(row=0,column=0,sticky='ew');toggle=ttk.Button(self.header_shell,text='▼ Design Header',command=self.toggle_header);toggle.pack(fill='x');self.header_toggle=toggle
        self.header=ttk.Frame(self.header_shell,padding=(8,5));self.header.pack(fill='x');self.header.columnconfigure(9,weight=1)
        ttk.Label(self.header,text='Template').grid(row=0,column=0);ttk.Combobox(self.header,textvariable=self.template,values=TEMPLATES,state='readonly',width=18).grid(row=0,column=1,padx=4);ttk.Button(self.header,text='New',command=self.new_template).grid(row=0,column=2)
        ttk.Button(self.header,text='Open Image',command=self.import_image).grid(row=0,column=3,padx=(8,0));ttk.Button(self.header,text='Save Project',command=self.save_project).grid(row=0,column=4,padx=4);ttk.Button(self.header,text='Open Project',command=self.open_project).grid(row=0,column=5);ttk.Button(self.header,text='Export PNG',command=self.export_png).grid(row=0,column=6,padx=4)
        ttk.Label(self.header,text='Grid').grid(row=0,column=7,padx=(10,2));ttk.Spinbox(self.header,from_=5,to=100,textvariable=self.grid,width=5,command=self.redraw).grid(row=0,column=8);ttk.Checkbutton(self.header,text='Snap',variable=self.snap).grid(row=0,column=9,sticky='w',padx=4)
        body=ttk.Panedwindow(self.parent,orient='horizontal');body.grid(row=1,column=0,sticky='nsew',padx=6,pady=5);left=ttk.Frame(body,padding=5);center=ttk.Frame(body);right=ttk.Frame(body,padding=5);body.add(left,weight=0);body.add(center,weight=1);body.add(right,weight=0)
        ttk.Label(left,text='Tools',font=('Segoe UI Semibold',11)).pack(anchor='w',pady=(0,4));toolbox=ttk.Frame(left);toolbox.pack(fill='x')
        for index,name in enumerate(TOOLS):ttk.Radiobutton(toolbox,text=name,value=name,variable=self.active_tool,command=self.tool_changed).grid(row=index//2,column=index%2,sticky='ew',padx=2,pady=2)
        dimensions=ttk.LabelFrame(left,text='Size & style',padding=5);dimensions.pack(fill='x',pady=7)
        for row,(label,var) in enumerate((('Width',self.shape_w),('Height',self.shape_h),('Scale',self.scale),('Stroke',self.stroke))):ttk.Label(dimensions,text=label).grid(row=row,column=0,sticky='w');ttk.Spinbox(dimensions,from_=1,to=10000,increment=.1,textvariable=var,width=9).grid(row=row,column=1,pady=2)
        ttk.Button(dimensions,text='Color',command=self.choose_color).grid(row=4,column=0,columnspan=2,sticky='ew',pady=(4,0))
        insert=ttk.LabelFrame(left,text='Modern inserts',padding=5);insert.pack(fill='x');cat=ttk.Combobox(insert,textvariable=self.insert_category,values=tuple(INSERTS),state='readonly',width=15);cat.pack(fill='x');cat.bind('<<ComboboxSelected>>',self.update_insert_items);self.insert_combo=ttk.Combobox(insert,textvariable=self.insert_item,values=INSERTS['Furniture'],state='readonly',width=15);self.insert_combo.pack(fill='x',pady=4);ttk.Button(insert,text='Place Item',command=lambda:self.active_tool.set('Insert')).pack(fill='x')
        uv=ttk.LabelFrame(left,text='UV Mapping',padding=5);uv.pack(fill='x',pady=(7,0));ttk.Entry(uv,textvariable=self.uv_path,width=18).pack(fill='x');buttons=ttk.Frame(uv);buttons.pack(fill='x',pady=4);ttk.Button(buttons,text='Open',command=self.choose_uv_input).pack(side='left',fill='x',expand=True);ttk.Button(buttons,text='Scan & Generate',command=self.scan_uv_input).pack(side='left',fill='x',expand=True,padx=(4,0));mode=ttk.Combobox(uv,textvariable=self.uv_mode,values=('Wireframe','Solid','Vertices'),state='readonly');mode.pack(fill='x');mode.bind('<<ComboboxSelected>>',self.change_uv_mode)
        self.canvas=tk.Canvas(center,bg='#f8fafc',highlightthickness=1,highlightbackground='#475569',cursor='crosshair');self.canvas.pack(fill='both',expand=True);self.canvas.bind('<Configure>',lambda _e:self.redraw());self.canvas.bind('<ButtonPress-1>',self.press);self.canvas.bind('<B1-Motion>',self.motion);self.canvas.bind('<ButtonRelease-1>',self.release);self.canvas.bind('<Motion>',self.pointer_info);self.canvas.bind('<Escape>',self.finish_line);self.canvas.focus_set()
        ttk.Label(right,text='Layers',font=('Segoe UI Semibold',11)).pack(anchor='w');layer_frame=ttk.Frame(right);layer_frame.pack(fill='both',expand=True);self.layer_list=tk.Listbox(layer_frame,width=28,height=18,bg='#0f172a',fg='white',exportselection=False);scroll=ttk.Scrollbar(layer_frame,orient='vertical',command=self.layer_list.yview);self.layer_list.configure(yscrollcommand=scroll.set);self.layer_list.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y');self.layer_list.bind('<<ListboxSelect>>',self.layer_selected)
        layer_buttons=ttk.Frame(right);layer_buttons.pack(fill='x',pady=4)
        for text,command in (('Hide',self.toggle_layer),('Color',self.layer_color),('Up',lambda:self.move_layer(-1)),('Down',lambda:self.move_layer(1)),('Delete',self.delete_layer)):ttk.Button(layer_buttons,text=text,command=command).pack(fill='x',pady=1)
        info=ttk.LabelFrame(right,text='Information',padding=6);info.pack(fill='x',pady=(5,0));ttk.Label(info,textvariable=self.info,wraplength=210,justify='left').pack(anchor='w')
        title=ttk.LabelFrame(right,text='Drawing information block',padding=6);title.pack(fill='x',pady=(5,0))
        self.title_fields={}
        defaults=(('Title','Project title'),('Drawing','A-001'),('Revision','A'),('Sheet','1 of 1'),('Scale','1:100'),('Drawn by',''),('Date',''))
        for row,(label,value) in enumerate(defaults):
            var=tk.StringVar(value=value);self.title_fields[label]=var;ttk.Label(title,text=label).grid(row=row,column=0,sticky='w');ttk.Entry(title,textvariable=var,width=16).grid(row=row,column=1,sticky='ew',padx=(4,0),pady=1)
        title.columnconfigure(1,weight=1);ttk.Button(title,text='Add information block',command=self.add_title_block).grid(row=len(defaults),column=0,columnspan=2,sticky='ew',pady=(5,0))
        ttk.Label(self.parent,textvariable=self.status).grid(row=2,column=0,sticky='ew',padx=8,pady=(0,5))
    def toggle_header(self):
        self.header_open=not self.header_open
        if self.header_open:self.header.pack(fill='x');self.header_toggle.config(text='▼ Design Header')
        else:self.header.pack_forget();self.header_toggle.config(text='▶ Design Header')
    def update_insert_items(self,_e=None):
        values=INSERTS[self.insert_category.get()];self.insert_combo.config(values=values);self.insert_item.set(values[0])
    def choose_color(self):
        color=colorchooser.askcolor(color=self.color,title='Choose drawing color')[1]
        if color:self.color=color
    def snap_value(self,value):
        size=max(1,self.grid.get());return round(value/size)*size if self.snap.get() else value
    def new_template(self):
        self.layers=[];self.next_id=1;self.selected=None;self.temp_points=[];name=self.template.get();w=max(600,self.canvas.winfo_width());h=max(420,self.canvas.winfo_height())
        if name=='Room Blueprint':self.add_layer('Room', 'rect',(90,70,w-90,h-70),'#111827',4)
        elif name=='House Grid':
            self.add_layer('Outer walls','rect',(55,45,w-55,h-45),'#111827',5);self.add_layer('Center wall','line',(w/2,45,w/2,h-45),'#111827',4);self.add_layer('Hall wall','line',(55,h*.55,w-55,h*.55),'#111827',4)
        elif name=='Cube UV Cross':
            s=min(w,h)/6;x=w/2-s*1.5;y=h/2-s/2
            for index,(dx,dy) in enumerate(((0,0),(1,0),(2,0),(3,0),(1,-1),(1,1))):self.add_layer(f'UV Face {index+1}','rect',(x+dx*s,y+dy*s,x+(dx+1)*s,y+(dy+1)*s),'#2563eb',2)
        elif name=='Cylinder UV':self.add_layer('Cylinder strip','rect',(w*.2,h*.25,w*.8,h*.7),'#2563eb',2);self.add_layer('Cap A','oval',(w*.08,h*.38,w*.18,h*.58),'#2563eb',2);self.add_layer('Cap B','oval',(w*.82,h*.38,w*.92,h*.58),'#2563eb',2)
        elif name=='Sphere UV Grid':
            self.add_layer('Sphere boundary','oval',(w*.2,h*.12,w*.8,h*.88),'#2563eb',2)
            for n in range(1,6):self.add_layer(f'UV Latitude {n}','oval',(w*(.2+n*.035),h*(.12+n*.06),w*(.8-n*.035),h*(.88-n*.06)),'#60a5fa',1)
        self.redraw();self.refresh_layers();self.status.set(f'Created {name}.')
    def add_layer(self,name,kind,coords,color=None,width=None,**extra):
        layer={'id':self.next_id,'name':name,'kind':kind,'coords':tuple(coords),'color':color or self.color,'width':width or self.stroke.get(),'hidden':False};layer.update(extra);self.next_id+=1;self.layers.append(layer);self.selected=layer['id'];self.refresh_layers();return layer
    def tool_changed(self):self.temp_points=[];self.status.set(f'{self.active_tool.get()} selected. Utility lines: click points, then press Esc to finish.')
    def press(self,event):
        x,y=self.snap_value(event.x),self.snap_value(event.y);tool=self.active_tool.get();self.canvas.focus_set()
        if tool in ('Electrical','Plumbing','Water'):
            self.temp_points.extend((x,y));self.redraw();return
        if tool=='Insert':self.insert_symbol(x,y);return
        if tool in ('Blur','Sharpen','Smudge'):self.apply_filter(tool,event.x,event.y);return
        hit=self.hit_layer(event.x,event.y)
        if tool=='Erase':
            if hit:self.layers.remove(hit);self.selected=None;self.refresh_layers();self.redraw()
            return
        if tool=='Clone Stamp':
            if hit:
                clone=dict(hit);clone['id']=self.next_id;self.next_id+=1;clone['name']=hit['name']+' Copy';clone['coords']=tuple(v+20 for v in hit['coords']);self.layers.append(clone);self.selected=clone['id'];self.refresh_layers();self.redraw()
            return
        if tool=='Select':
            self.selected=hit['id'] if hit else None;self.drag=(x,y,tuple(hit['coords'])) if hit else None;self.refresh_layers();self.redraw();return
        self.drag=(x,y,x,y);self.temp_points=[x,y]
    def motion(self,event):
        x,y=self.snap_value(event.x),self.snap_value(event.y);tool=self.active_tool.get()
        if tool=='Select' and self.drag and self.selected:
            layer=self.by_id(self.selected);dx=x-self.drag[0];dy=y-self.drag[1];original=self.drag[2];layer['coords']=tuple(value+(dx if index%2==0 else dy) for index,value in enumerate(original));self.redraw();self.update_info(layer);return
        if tool=='Paint' and self.drag:self.temp_points.extend((x,y));self.redraw();return
        if self.drag:self.drag=(self.drag[0],self.drag[1],x,y);self.redraw()
    def release(self,event):
        tool=self.active_tool.get()
        if tool=='Paint' and len(self.temp_points)>=4:self.add_layer('Paint stroke','polyline',self.temp_points);self.temp_points=[];self.drag=None;self.redraw();return
        if tool in ('Square','Triangle','Circle','Oval') and self.drag:
            x,y=self.drag[0],self.drag[1];w=self.shape_w.get()*self.scale.get();h=self.shape_h.get()*self.scale.get();kind={'Square':'rect','Circle':'oval','Oval':'oval','Triangle':'polygon'}[tool];coords=(x,y,x+w,y+h) if kind!='polygon' else (x+w/2,y,x+w,y+h,x,y+h);self.add_layer(tool,kind,coords);self.drag=None;self.redraw()
        elif tool=='Select':self.drag=None
    def finish_line(self,_event=None):
        if len(self.temp_points)>=4 and self.active_tool.get() in ('Electrical','Plumbing','Water'):
            tool=self.active_tool.get();colors={'Electrical':'#f59e0b','Plumbing':'#64748b','Water':'#2563eb'};self.add_layer(f'{tool} line','polyline',self.temp_points,colors[tool],3,utility=tool)
        self.temp_points=[];self.redraw();self.status.set('Point-to-point line finished.')
    def insert_symbol(self,x,y):
        name=self.insert_item.get();w=self.shape_w.get()*self.scale.get();h=self.shape_h.get()*self.scale.get();self.add_layer(name,'symbol',(x,y,x+w,y+h),category=self.insert_category.get());self.redraw()
    def choose_uv_input(self):
        path=filedialog.askopenfilename(title='Select model or image',filetypes=[('Models and images','*.obj *.fbx *.dae *.smd *.ascii *.cast *.psx *.png *.jpg *.jpeg *.bmp *.tga *.dds'),('All files','*.*')])
        if path:self.uv_path.set(path)
    def scan_uv_input(self):
        path=self.uv_path.get().strip()
        if not os.path.isfile(path):messagebox.showwarning('UV Mapping','Select a model or image first.');return
        try:
            extension=os.path.splitext(path)[1].lower();uvs=[];faces=[]
            if extension in ('.png','.jpg','.jpeg','.bmp','.tga','.dds','.tif','.tiff','.webp'):
                uvs=[(0,0),(1,0),(1,1),(0,1)];faces=[(0,1,2,3)]
            elif extension=='.obj':uvs,faces=self._scan_obj_uv(path)
            else:
                with open(path,'rb') as source:data=source.read()
                uvs,faces=self._scan_ascii_uv(data)
                if len(uvs)<3:uvs,faces=self._scan_binary_uv(data)
            if len(uvs)<3:raise ValueError('No usable UV coordinate buffer was found. Try an OBJ export or the 3D Model scanner first.')
            # Replace the previous generated layout while leaving other Design layers intact.
            if self.uv_layer_id:
                old=self.by_id(self.uv_layer_id)
                if old:self.layers.remove(old)
            layer=self.add_layer(f'UV Layout - {os.path.basename(path)}','uvmesh',(20,20,600,420),'#22d3ee',1,uvs=uvs,faces=faces,mode=self.uv_mode.get(),source=path);self.uv_layer_id=layer['id'];self.redraw();self.status.set(f'Generated flat UV layout: {len(uvs):,} vertices, {len(faces):,} faces.')
        except Exception as error:messagebox.showerror('UV Mapping',str(error))
    def _scan_obj_uv(self,path):
        uvs=[];faces=[]
        with open(path,encoding='utf-8',errors='ignore') as source:
            for line in source:
                parts=line.strip().split()
                if len(parts)>=3 and parts[0]=='vt':uvs.append((float(parts[1]),float(parts[2])))
                elif len(parts)>=4 and parts[0]=='f':
                    face=[]
                    for token in parts[1:]:
                        fields=token.split('/')
                        if len(fields)>1 and fields[1]:face.append(int(fields[1])-1 if int(fields[1])>0 else len(uvs)+int(fields[1]))
                    if len(face)>=3:faces.append(tuple(face))
        return uvs,faces
    def _scan_ascii_uv(self,data):
        text=data.decode('utf-8','ignore');uvs=[];faces=[]
        match=re.search(r'UV\s*:\s*\*?\d+\s*\{\s*a\s*:\s*([^}]*)',text,re.I|re.S)
        if match:
            numbers=[float(v) for v in re.findall(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?',match.group(1))];uvs=list(zip(numbers[0::2],numbers[1::2]))
            index_match=re.search(r'UVIndex\s*:\s*\*?\d+\s*\{\s*a\s*:\s*([^}]*)',text,re.I|re.S)
            if index_match:
                current=[]
                for value in (int(v) for v in re.findall(r'-?\d+',index_match.group(1))):
                    if value<0:current.append(-value-1);faces.append(tuple(current));current=[]
                    else:current.append(value)
        return uvs,faces
    def _scan_binary_uv(self,data):
        # Generic fallback: locate the longest aligned Float32 UV run in 0..1.
        best=[]
        for endian in ('<','>'):
            run=[]
            for offset in range(0,len(data)-8,8):
                try:u,v=struct.unpack_from(endian+'ff',data,offset)
                except struct.error:break
                if math.isfinite(u) and math.isfinite(v) and -.001<=u<=1.001 and -.001<=v<=1.001:run.append((u,v))
                else:
                    if len(run)>len(best):best=run[:]
                    run=[]
                if len(run)>=250000:break
            if len(run)>len(best):best=run
        faces=[tuple(range(index,index+3)) for index in range(0,len(best)-2,3)];return best,faces
    def change_uv_mode(self,_event=None):
        layer=self.by_id(self.uv_layer_id) if self.uv_layer_id else None
        if layer:layer['mode']=self.uv_mode.get();self.redraw()
    def add_title_block(self):
        w=max(620,self.canvas.winfo_width());h=max(430,self.canvas.winfo_height());block_w=min(520,w-40);block_h=145
        fields={name:var.get().strip() for name,var in self.title_fields.items()}
        self.add_layer('Drawing information','titleblock',(w-block_w-18,h-block_h-18,w-18,h-18),'#111827',2,fields=fields)
        self.redraw();self.status.set('Drawing information block added as a new layer.')
    def import_image(self):
        path=filedialog.askopenfilename(filetypes=[('Images','*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp'),('All files','*.*')])
        if not path:return
        try:
            from PIL import Image
            with Image.open(path) as im:w,h=im.size
            self.add_layer(os.path.basename(path),'image',(40,40,40+w,40+h),path=path);self.redraw()
        except Exception as error:messagebox.showerror('Open image',str(error))
    def apply_filter(self,name,x,y):
        layer=self.hit_layer(x,y)
        if not layer or layer['kind']!='image':self.status.set(f'{name} requires an imported image layer.');return
        layer['filter']=name;self.selected=layer['id'];self.redraw();self.status.set(f'{name} applied to {layer["name"]}.')
    def hit_layer(self,x,y):
        items=self.canvas.find_overlapping(x,y,x,y)
        for item in reversed(items):
            for tag in self.canvas.gettags(item):
                if tag.startswith('layer:'):
                    return self.by_id(int(tag.split(':')[1]))
        return None
    def by_id(self,layer_id):return next((layer for layer in self.layers if layer['id']==layer_id),None)
    def redraw(self):
        c=self.canvas;c.delete('all');w=max(1,c.winfo_width());h=max(1,c.winfo_height());grid=max(5,self.grid.get())
        for x in range(0,w,grid):c.create_line(x,0,x,h,fill='#e2e8f0')
        for y in range(0,h,grid):c.create_line(0,y,w,y,fill='#e2e8f0')
        for layer in self.layers:
            if not layer['hidden']:self.draw_layer(layer)
        if self.temp_points:
            if self.active_tool.get() in ('Electrical','Plumbing','Water'):c.create_line(*self.temp_points,fill={'Electrical':'#f59e0b','Plumbing':'#64748b','Water':'#2563eb'}[self.active_tool.get()],width=3,dash=(7,3))
            elif self.active_tool.get()=='Paint' and len(self.temp_points)>=4:c.create_line(*self.temp_points,fill=self.color,width=self.stroke.get(),smooth=True)
    def draw_layer(self,layer):
        c=self.canvas;tag=(f'layer:{layer["id"]}','design');coords=layer['coords'];color=layer['color'];width=layer['width'];kind=layer['kind']
        if kind=='rect':item=c.create_rectangle(*coords,outline=color,width=width,tags=tag)
        elif kind=='oval':item=c.create_oval(*coords,outline=color,width=width,tags=tag)
        elif kind=='polygon':item=c.create_polygon(*coords,fill='',outline=color,width=width,tags=tag)
        elif kind in ('line','polyline'):item=c.create_line(*coords,fill=color,width=width,smooth=False,tags=tag)
        elif kind=='symbol':item=self.draw_symbol(layer,tag)
        elif kind=='uvmesh':item=self.draw_uvmesh(layer,tag)
        elif kind=='titleblock':item=self.draw_titleblock(layer,tag)
        elif kind=='image':item=self.draw_image(layer,tag)
        else:return
        if layer['id']==self.selected:
            box=c.bbox(item)
            if box:c.create_rectangle(*box,outline='#22c55e',dash=(5,3),width=2,tags='selection')
    def draw_symbol(self,layer,tag):
        c=self.canvas;x1,y1,x2,y2=layer['coords'];name=layer['name'];color=layer['color'];w=layer['width'];group=f'layer:{layer["id"]}'
        main=c.create_rectangle(x1,y1,x2,y2,outline=color,width=w,tags=tag)
        if any(word in name for word in ('Sofa','Bed','Cabinet','Island','Table','Desk','Nightstand','Refrigerator','Washer','Dryer')):c.create_rectangle(x1+8,y1+8,x2-8,y2-8,outline=color,width=1,tags=tag)
        if name in ('Stove','Sink','Ceiling Light','Lamp','Outlet','Switch','Toilet','Bathtub'):
            c.create_oval(x1+8,y1+8,x2-8,y2-8,outline=color,width=max(1,w),tags=tag)
        c.create_text((x1+x2)/2,(y1+y2)/2,text=name,fill=color,font=('Segoe UI',8),tags=tag);return main
    def draw_uvmesh(self,layer,tag):
        c=self.canvas;uvs=layer.get('uvs',[]);faces=layer.get('faces',[]);mode=layer.get('mode','Wireframe');margin=28;w=max(80,c.winfo_width()-margin*2);h=max(80,c.winfo_height()-margin*2);color=layer['color'];first=None
        points=[(margin+u*w,margin+(1-v)*h) for u,v in uvs]
        c.create_rectangle(margin,margin,margin+w,margin+h,outline='#64748b',dash=(4,3),tags=tag)
        if mode in ('Wireframe','Solid'):
            for face in faces:
                polygon=[coord for index in face if 0<=index<len(points) for coord in points[index]]
                if len(polygon)>=6:
                    item=c.create_polygon(*polygon,fill='#164e63' if mode=='Solid' else '',stipple='gray25' if mode=='Solid' else '',outline=color,width=1,tags=tag);first=first or item
        if mode=='Vertices' or not faces:
            for x,y in points[:100000]:
                item=c.create_oval(x-2,y-2,x+2,y+2,fill=color,outline='',tags=tag);first=first or item
        return first or c.create_text(margin+6,margin+6,text='No UV faces',fill=color,anchor='nw',tags=tag)
    def draw_titleblock(self,layer,tag):
        c=self.canvas;x1,y1,x2,y2=layer['coords'];color=layer['color'];fields=layer.get('fields',{});mid=x1+(x2-x1)*.62;row=(y2-y1)/4
        main=c.create_rectangle(x1,y1,x2,y2,outline=color,width=2,tags=tag);c.create_line(mid,y1,mid,y2,fill=color,width=1,tags=tag)
        for n in range(1,4):c.create_line(mid,y1+n*row,x2,y1+n*row,fill=color,width=1,tags=tag)
        c.create_text(x1+10,y1+12,text='TITLE / PROJECT',anchor='w',fill=color,font=('Segoe UI',7),tags=tag);c.create_text(x1+10,y1+34,text=fields.get('Title',''),anchor='w',fill=color,font=('Segoe UI Semibold',12),tags=tag)
        c.create_text(x1+10,y2-28,text=f"DRAWING  {fields.get('Drawing','')}     SCALE  {fields.get('Scale','')}",anchor='w',fill=color,font=('Segoe UI',8),tags=tag)
        rows=(('REVISION','Revision'),('SHEET','Sheet'),('DRAWN BY','Drawn by'),('DATE','Date'))
        for n,(label,key) in enumerate(rows):c.create_text(mid+8,y1+n*row+7,text=label,anchor='nw',fill=color,font=('Segoe UI',7),tags=tag);c.create_text(mid+8,y1+n*row+22,text=fields.get(key,''),anchor='nw',fill=color,font=('Segoe UI Semibold',9),tags=tag)
        return main
    def draw_image(self,layer,tag):
        try:
            from PIL import Image,ImageEnhance,ImageFilter,ImageTk
            x1,y1,x2,y2=layer['coords'];im=Image.open(layer['path']).convert('RGBA').resize((max(1,int(x2-x1)),max(1,int(y2-y1))))
            effect=layer.get('filter')
            if effect=='Blur':im=im.filter(ImageFilter.GaussianBlur(2))
            elif effect=='Sharpen':im=ImageEnhance.Sharpness(im).enhance(2.2)
            elif effect=='Smudge':im=im.filter(ImageFilter.GaussianBlur(1)).filter(ImageFilter.SMOOTH_MORE)
            photo=ImageTk.PhotoImage(im);self.photos[layer['id']]=photo;return self.canvas.create_image(x1,y1,image=photo,anchor='nw',tags=tag)
        except Exception:return self.canvas.create_rectangle(*layer['coords'],outline='#ef4444',tags=tag)
    def pointer_info(self,event):self.info.set(f'X {event.x:.0f}  |  Y {event.y:.0f}  |  Width {self.shape_w.get():.1f}  |  Height {self.shape_h.get():.1f}  |  Distance 0')
    def update_info(self,layer):
        xs=layer['coords'][0::2];ys=layer['coords'][1::2];width=max(xs)-min(xs);height=max(ys)-min(ys);distance=sum(math.hypot(layer['coords'][i+2]-layer['coords'][i],layer['coords'][i+3]-layer['coords'][i+1]) for i in range(0,len(layer['coords'])-2,2));self.info.set(f'X {min(xs):.1f}  |  Y {min(ys):.1f}\nWidth {width:.1f}  |  Height {height:.1f}\nDistance {distance:.2f}')
    def refresh_layers(self):
        self.layer_list.delete(0,'end')
        for layer in reversed(self.layers):self.layer_list.insert('end',('○ ' if layer['hidden'] else '● ')+layer['name'])
        if self.selected:
            index=next((i for i,l in enumerate(reversed(self.layers)) if l['id']==self.selected),None)
            if index is not None:self.layer_list.selection_set(index)
    def layer_selected(self,_e=None):
        selection=self.layer_list.curselection()
        if selection:self.selected=list(reversed(self.layers))[selection[0]]['id'];self.update_info(self.by_id(self.selected));self.redraw()
    def selected_layer(self):return self.by_id(self.selected) if self.selected else None
    def toggle_layer(self):
        layer=self.selected_layer()
        if layer:layer['hidden']=not layer['hidden'];self.refresh_layers();self.redraw()
    def layer_color(self):
        layer=self.selected_layer()
        if not layer:return
        color=colorchooser.askcolor(color=layer['color'])[1]
        if color:layer['color']=color;self.redraw()
    def move_layer(self,direction):
        layer=self.selected_layer()
        if not layer:return
        index=self.layers.index(layer);target=max(0,min(len(self.layers)-1,index-direction))
        if target!=index:self.layers.insert(target,self.layers.pop(index));self.refresh_layers();self.redraw()
    def delete_layer(self):
        layer=self.selected_layer()
        if layer:self.layers.remove(layer);self.selected=None;self.refresh_layers();self.redraw()
    def save_project(self):
        path=filedialog.asksaveasfilename(defaultextension='.aidesign',filetypes=[('AI Design','*.aidesign')])
        if path:
            with open(path,'w',encoding='utf-8') as output:json.dump({'layers':self.layers,'grid':self.grid.get()},output,indent=2)
    def open_project(self):
        path=filedialog.askopenfilename(filetypes=[('AI Design','*.aidesign'),('JSON','*.json')])
        if not path:return
        try:
            with open(path,encoding='utf-8') as source:data=json.load(source)
            self.layers=data.get('layers',[]);self.grid.set(data.get('grid',20));self.next_id=max((l['id'] for l in self.layers),default=0)+1;self.selected=None;self.refresh_layers();self.redraw()
        except Exception as error:messagebox.showerror('Open project',str(error))
    def export_png(self):
        path=filedialog.asksaveasfilename(defaultextension='.png',filetypes=[('PNG','*.png')])
        if not path:return
        try:
            from PIL import Image,ImageDraw
            image=Image.new('RGBA',(max(1,self.canvas.winfo_width()),max(1,self.canvas.winfo_height())),'white');draw=ImageDraw.Draw(image)
            for layer in self.layers:
                if layer['hidden']:continue
                coords=layer['coords'];color=layer['color'];width=max(1,int(layer['width']));kind=layer['kind']
                if kind=='rect':draw.rectangle(coords,outline=color,width=width)
                elif kind=='oval':draw.ellipse(coords,outline=color,width=width)
                elif kind=='polygon':draw.polygon(list(zip(coords[0::2],coords[1::2])),outline=color)
                elif kind in ('line','polyline'):draw.line(coords,fill=color,width=width,joint='curve')
                elif kind=='symbol':draw.rectangle(coords,outline=color,width=width);draw.text((coords[0]+5,coords[1]+5),layer['name'],fill=color)
                elif kind=='uvmesh':
                    margin=28;canvas_w=image.width-margin*2;canvas_h=image.height-margin*2;points=[(margin+u*canvas_w,margin+(1-v)*canvas_h) for u,v in layer.get('uvs',[])];mode=layer.get('mode','Wireframe');draw.rectangle((margin,margin,margin+canvas_w,margin+canvas_h),outline='#64748b',width=1)
                    if mode in ('Wireframe','Solid'):
                        for face in layer.get('faces',[]):
                            polygon=[points[index] for index in face if 0<=index<len(points)]
                            if len(polygon)>=3:draw.polygon(polygon,fill='#164e63' if mode=='Solid' else None,outline=color)
                    if mode=='Vertices' or not layer.get('faces'):
                        for x,y in points[:100000]:draw.ellipse((x-2,y-2,x+2,y+2),fill=color)
                elif kind=='titleblock':
                    x1,y1,x2,y2=coords;mid=x1+(x2-x1)*.62;row=(y2-y1)/4;fields=layer.get('fields',{});draw.rectangle(coords,outline=color,width=width);draw.line((mid,y1,mid,y2),fill=color,width=1)
                    for n in range(1,4):draw.line((mid,y1+n*row,x2,y1+n*row),fill=color,width=1)
                    draw.text((x1+8,y1+8),'TITLE / PROJECT',fill=color);draw.text((x1+8,y1+27),fields.get('Title',''),fill=color);draw.text((x1+8,y2-22),f"DRAWING {fields.get('Drawing','')}   SCALE {fields.get('Scale','')}",fill=color)
                    for n,(label,key) in enumerate((('REVISION','Revision'),('SHEET','Sheet'),('DRAWN BY','Drawn by'),('DATE','Date'))):draw.text((mid+6,y1+n*row+5),f"{label}: {fields.get(key,'')}",fill=color)
                elif kind=='image':
                    try:
                        source=Image.open(layer['path']).convert('RGBA').resize((int(coords[2]-coords[0]),int(coords[3]-coords[1])));image.alpha_composite(source,(int(coords[0]),int(coords[1])))
                    except Exception:pass
            image.convert('RGB').save(path);self.status.set(f'Exported {path}')
        except Exception as error:messagebox.showerror('Export PNG',str(error))


def build_design_tool(parent):return DesignTool(parent)
