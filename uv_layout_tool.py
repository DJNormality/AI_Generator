"""Interactive split-view UV editor for AI Generator."""
import math, random, tkinter as tk
from collections import defaultdict, deque
from tkinter import filedialog, messagebox, ttk

METHODS=('Use Existing UV','Auto UV','Random Selected Parts','Flat','Edge Projection','Projection Top','Projection Bottom','Projection Left','Projection Right','Planar XY','Planar XZ','Planar YZ','Box Projection','Cylindrical','Spherical','Shrink Wrap','Peel / Seam','Symmetrical','Line')
MESH_MODES=('Polygons','Lines','Vertices');UV_MODES=('Wireframe','Solid','Vertices')

class UVLayoutTool:
    def __init__(self,parent):
        self.parent=parent;self.path='';self.vertices=[];self.faces=[];self.uvs=[];self.uv_faces=[]
        self.selected_faces=set();self.selected_edges=set();self.selected_vertices=set();self.edge_faces=defaultdict(list)
        self.uv_zoom=1.;self.uv_pan=[0.,0.];self.uv_drag=None;self.model_zoom=1.;self.model_pan=[0.,0.];self.model_drag=None;self.yaw=.55;self.pitch=-.35
        self.method=tk.StringVar(value='Auto UV');self.mesh_mode=tk.StringVar(value='Polygons');self.uv_mode=tk.StringVar(value='Wireframe');self.symmetry=tk.StringVar(value='X')
        self.status=tk.StringVar(value='Open an OBJ model, then select faces or edge loops in the model viewport.');self._build()
    def _build(self):
        top=ttk.Frame(self.parent,padding=(8,6));top.pack(fill='x');self.path_var=tk.StringVar();ttk.Entry(top,textvariable=self.path_var).pack(side='left',fill='x',expand=True);ttk.Button(top,text='Open Model',command=self.open_model).pack(side='left',padx=5);ttk.Combobox(top,textvariable=self.method,values=METHODS,state='readonly',width=22).pack(side='left');ttk.Button(top,text='Generate All',command=lambda:self.generate(False)).pack(side='left',padx=4);ttk.Button(top,text='Generate From Selection',command=lambda:self.generate(True)).pack(side='left');ttk.Button(top,text='Auto UV Selected',command=self.auto_uv_selected).pack(side='left',padx=4)
        tools=ttk.Frame(self.parent,padding=(8,0,8,5));tools.pack(fill='x');ttk.Label(tools,text='Mesh').pack(side='left');ttk.Combobox(tools,textvariable=self.mesh_mode,values=MESH_MODES,state='readonly',width=11).pack(side='left',padx=(4,10));ttk.Label(tools,text='UV').pack(side='left');ttk.Combobox(tools,textvariable=self.uv_mode,values=UV_MODES,state='readonly',width=11).pack(side='left',padx=(4,10));ttk.Button(tools,text='Select Loop',command=self.select_loop).pack(side='left');ttk.Button(tools,text='Apply Loops to UV',command=self.apply_loops).pack(side='left',padx=4);ttk.Button(tools,text='Clear Selection',command=self.clear_selection).pack(side='left');ttk.Label(tools,text='Symmetry').pack(side='left',padx=(12,3));ttk.Combobox(tools,textvariable=self.symmetry,values=('X','Y','Z'),state='readonly',width=4).pack(side='left');ttk.Button(tools,text='Fit Both',command=self.fit).pack(side='right')
        split=ttk.Panedwindow(self.parent,orient='horizontal');split.pack(fill='both',expand=True,padx=8);model=ttk.Frame(split);uv=ttk.Frame(split);split.add(model,weight=1);split.add(uv,weight=1)
        ttk.Label(model,text='Model — wheel zoom • drag rotate • middle-drag move • Alt+click select • Ctrl+click deselect').pack(anchor='w');self.model_canvas=tk.Canvas(model,bg='#020617',highlightthickness=1,highlightbackground='#334155');self.model_canvas.pack(fill='both',expand=True)
        ttk.Label(uv,text='UV — wheel zoom • drag move • selected loops are orange').pack(anchor='w');self.uv_canvas=tk.Canvas(uv,bg='#020617',highlightthickness=1,highlightbackground='#334155');self.uv_canvas.pack(fill='both',expand=True)
        self.model_canvas.bind('<MouseWheel>',self.model_wheel);self.model_canvas.bind('<ButtonPress-1>',self.model_press);self.model_canvas.bind('<B1-Motion>',self.model_motion);self.model_canvas.bind('<ButtonRelease-1>',self.model_release);self.model_canvas.bind('<ButtonPress-2>',self.model_pan_start);self.model_canvas.bind('<B2-Motion>',self.model_pan_move)
        self.uv_canvas.bind('<MouseWheel>',self.uv_wheel);self.uv_canvas.bind('<ButtonPress-1>',self.uv_pan_start);self.uv_canvas.bind('<B1-Motion>',self.uv_pan_move);self.model_canvas.bind('<Configure>',lambda _e:self.draw_model());self.uv_canvas.bind('<Configure>',lambda _e:self.draw_uv());self.mesh_mode.trace_add('write',lambda *_:self.draw_model());self.uv_mode.trace_add('write',lambda *_:self.draw_uv())
        bottom=ttk.Frame(self.parent,padding=8);bottom.pack(fill='x');ttk.Button(bottom,text='Export UV PNG',command=self.export_png).pack(side='left');ttk.Button(bottom,text='Export OBJ with UV',command=self.export_obj).pack(side='left',padx=5);ttk.Label(bottom,textvariable=self.status).pack(side='left',padx=10)
    def open_model(self):
        path=filedialog.askopenfilename(title='Open model for UV layout',filetypes=[('OBJ model','*.obj'),('All files','*.*')])
        if not path:return
        try:self._read_obj(path);self.path=path;self.path_var.set(path);self._build_topology();self.clear_selection(False);self.method.set('Use Existing UV' if self.uvs else 'Auto UV');self.generate(False);self.fit()
        except Exception as error:messagebox.showerror('UV Layout',str(error))
    def _read_obj(self,path):
        vertices=[];uvs=[];faces=[];uv_faces=[]
        with open(path,'r',encoding='utf-8',errors='ignore') as stream:
            for line in stream:
                parts=line.strip().split()
                if not parts:continue
                if parts[0]=='v' and len(parts)>=4:vertices.append(tuple(map(float,parts[1:4])))
                elif parts[0]=='vt' and len(parts)>=3:uvs.append(tuple(map(float,parts[1:3])))
                elif parts[0]=='f' and len(parts)>=4:
                    vi=[];ti=[]
                    for token in parts[1:]:
                        fields=token.split('/');v=int(fields[0]);vi.append(v-1 if v>0 else len(vertices)+v)
                        if len(fields)>1 and fields[1]:t=int(fields[1]);ti.append(t-1 if t>0 else len(uvs)+t)
                    faces.append(tuple(vi));uv_faces.append(tuple(ti) if len(ti)==len(vi) else tuple(vi))
        if not vertices:raise ValueError('No OBJ vertices were found. Export the model as OBJ first.')
        self.vertices,self.faces,self.uvs,self.uv_faces=vertices,faces,uvs,uv_faces
    def _build_topology(self):
        self.edge_faces=defaultdict(list)
        for face_id,face in enumerate(self.faces):
            for index,a in enumerate(face):self.edge_faces[tuple(sorted((a,face[(index+1)%len(face)])))].append(face_id)
    @staticmethod
    def _norm(values):low=min(values);span=max(values)-low or 1.;return [(value-low)/span for value in values]
    def _projection(self,method):
        xs,ys,zs=zip(*self.vertices);nx,ny,nz=self._norm(xs),self._norm(ys),self._norm(zs)
        if method in ('Flat','Projection Top','Planar XZ'):return list(zip(nx,nz))
        if method=='Projection Bottom':return [(u,1-v) for u,v in zip(nx,nz)]
        if method in ('Projection Left','Planar YZ'):return list(zip(nz,ny))
        if method=='Projection Right':return [(1-u,v) for u,v in zip(nz,ny)]
        if method=='Planar XY':return list(zip(nx,ny))
        if method=='Edge Projection':return list(zip(nx,ny)) if (max(zs)-min(zs))<=(max(xs)-min(xs)) else list(zip(nz,ny))
        if method in ('Cylindrical','Peel / Seam'):
            ymin,yspan=min(ys),max(ys)-min(ys) or 1.;return [((math.atan2(z,x)/(2*math.pi)+.5)%1,(y-ymin)/yspan) for x,y,z in self.vertices]
        if method in ('Spherical','Shrink Wrap'):
            result=[]
            for x,y,z in self.vertices:radius=math.sqrt(x*x+y*y+z*z) or 1.;result.append(((math.atan2(z,x)/(2*math.pi)+.5)%1,.5-math.asin(max(-1,min(1,y/radius)))/math.pi))
            return result
        if method=='Box Projection':
            result=[]
            for i,(x,y,z) in enumerate(self.vertices):
                ax,ay,az=abs(x),abs(y),abs(z);result.append((ny[i],nz[i]) if ax>=ay and ax>=az else (nx[i],nz[i]) if ay>=az else (nx[i],ny[i]))
            return result
        if method=='Symmetrical':
            axis=self.symmetry.get();base=list(zip(ny,nz)) if axis=='X' else list(zip(nx,nz)) if axis=='Y' else list(zip(nx,ny));coords=xs if axis=='X' else ys if axis=='Y' else zs
            return [(1-abs(u-.5)*2 if value<0 else abs(u-.5)*2,v) for (u,v),value in zip(base,coords)]
        if method=='Line':count=max(1,len(self.vertices)-1);return [(i/count,.5) for i in range(len(self.vertices))]
        spans=(max(xs)-min(xs),max(ys)-min(ys),max(zs)-min(zs));small=spans.index(min(spans));return list(zip(ny,nz)) if small==0 else list(zip(nx,nz)) if small==1 else list(zip(nx,ny))
    def generate(self,selection_only=False):
        if not self.vertices:messagebox.showwarning('UV Layout','Open a model first.');return
        method=self.method.get()
        if method=='Use Existing UV' and self.uvs and not selection_only:self.status.set(f'Using {len(self.uvs):,} original UV coordinates.');self.fit();return
        generated=self._random_islands(selection_only or method=='Random Selected Parts') if method in ('Auto UV','Random Selected Parts') else self._projection(method);targets=self._selected_vertex_ids() if selection_only else set(range(len(self.vertices)))
        if selection_only and not targets:messagebox.showwarning('UV Layout','Select polygons, lines, vertices, or a loop first.');return
        if len(self.uvs)!=len(self.vertices):self.uvs=[(.5,.5)]*len(self.vertices);self.uv_faces=[tuple(face) for face in self.faces]
        for index in targets:self.uvs[index]=generated[index]
        self.status.set(f'Generated {len(targets):,} UV point(s) using {method}.');self.draw_uv();self.draw_model()
    def _random_islands(self,selection_only=False):
        rng=random.Random() if selection_only else random.Random(0xA17E);base=self._projection('Box Projection');targets=self._selected_vertex_ids() if selection_only else set(range(len(self.vertices)));result=list(self.uvs) if len(self.uvs)==len(self.vertices) else [(.5,.5)]*len(self.vertices);angle=rng.uniform(-math.pi,math.pi);scale=rng.uniform(.28,.72);cx,cy=rng.uniform(.2,.8),rng.uniform(.2,.8);ca,sa=math.cos(angle),math.sin(angle)
        for index in targets:u,v=base[index];x,y=(u-.5)*scale,(v-.5)*scale;result[index]=(max(0,min(1,cx+x*ca-y*sa)),max(0,min(1,cy+x*sa+y*ca)))
        return result
    def auto_uv_selected(self):self.method.set('Random Selected Parts');self.generate(True)
    def _selected_vertex_ids(self):
        vertices=set(self.selected_vertices)
        for face_id in self.selected_faces:
            if face_id<len(self.faces):vertices.update(self.faces[face_id])
        for edge in self.selected_edges:vertices.update(edge)
        return vertices
    def clear_selection(self,redraw=True):
        self.selected_faces.clear();self.selected_edges.clear();self.selected_vertices.clear()
        if redraw:self.draw_model();self.draw_uv();self.status.set('Selection cleared.')
    def select_loop(self):
        if not self.selected_edges:messagebox.showwarning('UV Layout','Switch Mesh to Lines and Alt-click an edge first.');return
        queue=deque(self.selected_edges);visited=set(self.selected_edges)
        while queue:
            edge=queue.popleft()
            for vertex in edge:
                candidates=[candidate for candidate in self.edge_faces if vertex in candidate and candidate not in visited]
                if not candidates:continue
                other=edge[0] if edge[1]==vertex else edge[1];vector=[self.vertices[vertex][i]-self.vertices[other][i] for i in range(3)]
                def score(candidate):
                    nxt=candidate[0] if candidate[1]==vertex else candidate[1];direction=[self.vertices[nxt][i]-self.vertices[vertex][i] for i in range(3)];a=math.sqrt(sum(v*v for v in vector)) or 1;b=math.sqrt(sum(v*v for v in direction)) or 1;return sum(vector[i]*direction[i] for i in range(3))/(a*b)
                candidate=max(candidates,key=score)
                if score(candidate)>.35:visited.add(candidate);queue.append(candidate)
        self.selected_edges=visited;self.draw_model();self.draw_uv();self.status.set(f'Selected edge loop: {len(visited):,} edges.')
    def apply_loops(self):
        if not self.selected_edges:messagebox.showwarning('UV Layout','Select an edge loop first.');return
        self.selected_faces={face for edge in self.selected_edges for face in self.edge_faces.get(edge,())};self.draw_model();self.draw_uv();self.status.set(f'Applied loop boundary to {len(self.selected_faces):,} UV polygons.')
    def fit(self):self.uv_zoom=self.model_zoom=1.;self.uv_pan=[0.,0.];self.model_pan=[0.,0.];self.draw_model();self.draw_uv()
    def uv_wheel(self,event):self.uv_zoom=max(.08,min(40,self.uv_zoom*(1.2 if event.delta>0 else 1/1.2)));self.draw_uv();return 'break'
    def model_wheel(self,event):self.model_zoom=max(.08,min(40,self.model_zoom*(1.2 if event.delta>0 else 1/1.2)));self.draw_model();return 'break'
    def uv_pan_start(self,event):self.uv_drag=(event.x,event.y,*self.uv_pan)
    def uv_pan_move(self,event):
        if self.uv_drag:x,y,px,py=self.uv_drag;self.uv_pan=[px+event.x-x,py+event.y-y];self.draw_uv()
    def model_pan_start(self,event):self.model_drag=('pan',event.x,event.y,*self.model_pan)
    def model_pan_move(self,event):
        if self.model_drag and self.model_drag[0]=='pan':_,x,y,px,py=self.model_drag;self.model_pan=[px+event.x-x,py+event.y-y];self.draw_model()
    def model_press(self,event):
        alt=bool(event.state&0x0008);ctrl=bool(event.state&0x0004)
        if alt or ctrl:self._pick(event.x,event.y,remove=ctrl);return 'break'
        self.model_drag=('rotate',event.x,event.y,self.yaw,self.pitch)
    def model_motion(self,event):
        if self.model_drag and self.model_drag[0]=='rotate':_,x,y,yaw,pitch=self.model_drag;self.yaw=yaw+(event.x-x)*.009;self.pitch=max(-1.5,min(1.5,pitch+(event.y-y)*.009));self.draw_model()
    def model_release(self,_event):self.model_drag=None
    def _model_points(self):
        if not self.vertices:return []
        cy,sy=math.cos(self.yaw),math.sin(self.yaw);cp,sp=math.cos(self.pitch),math.sin(self.pitch);rot=[]
        for x,y,z in self.vertices:x,z=x*cy-z*sy,x*sy+z*cy;y,z=y*cp-z*sp,y*sp+z*cp;rot.append((x,y,z))
        xs=[p[0] for p in rot];ys=[p[1] for p in rot];span=max(max(xs)-min(xs),max(ys)-min(ys),1e-9);w=max(2,self.model_canvas.winfo_width());h=max(2,self.model_canvas.winfo_height());scale=min(w,h)*.78/span*self.model_zoom;cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2;return [(w/2+(x-cx)*scale+self.model_pan[0],h/2-(y-cy)*scale+self.model_pan[1],z) for x,y,z in rot]
    def _pick(self,x,y,remove=False):
        points=self._model_points();mode=self.mesh_mode.get();target=None;best=14.
        if mode=='Vertices':
            for index,(px,py,_) in enumerate(points):
                distance=math.hypot(x-px,y-py)
                if distance<best:best=distance;target=index
            if target is not None:(self.selected_vertices.discard if remove else self.selected_vertices.add)(target)
        elif mode=='Lines':
            for edge in self.edge_faces:
                distance=self._segment_distance(x,y,points[edge[0]][:2],points[edge[1]][:2])
                if distance<best:best=distance;target=edge
            if target is not None:(self.selected_edges.discard if remove else self.selected_edges.add)(target)
        else:
            for face_id,face in enumerate(self.faces):
                if self._inside(x,y,[points[i][:2] for i in face]):target=face_id
            if target is not None:(self.selected_faces.discard if remove else self.selected_faces.add)(target)
        self.draw_model();self.draw_uv();self.status.set(f'Selected: {len(self.selected_faces)} polygons, {len(self.selected_edges)} lines, {len(self.selected_vertices)} vertices.')
    @staticmethod
    def _segment_distance(x,y,a,b):
        dx,dy=b[0]-a[0],b[1]-a[1];length=dx*dx+dy*dy
        if not length:return math.hypot(x-a[0],y-a[1])
        t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/length));return math.hypot(x-(a[0]+t*dx),y-(a[1]+t*dy))
    @staticmethod
    def _inside(x,y,polygon):
        inside=False;j=len(polygon)-1
        for i,(xi,yi) in enumerate(polygon):
            xj,yj=polygon[j]
            if ((yi>y)!=(yj>y)) and x<(xj-xi)*(y-yi)/(yj-yi or 1e-9)+xi:inside=not inside
            j=i
        return inside
    def draw_model(self):
        c=self.model_canvas;c.delete('all');points=self._model_points()
        if not points:return
        order=sorted(range(len(self.faces)),key=lambda i:sum(points[v][2] for v in self.faces[i])/len(self.faces[i]))
        for face_id in order:
            face=self.faces[face_id];coords=[value for vertex in face for value in points[vertex][:2]];selected=face_id in self.selected_faces;fill='#7c2d12' if selected else '#123047' if self.mesh_mode.get()=='Polygons' else '';c.create_polygon(*coords,fill=fill,outline='#fb923c' if selected else '#67e8f9',width=2 if selected else 1)
        for edge in self.selected_edges:a,b=points[edge[0]],points[edge[1]];c.create_line(a[0],a[1],b[0],b[1],fill='#f97316',width=4)
        if self.mesh_mode.get()=='Vertices':
            for index,(x,y,_) in enumerate(points):c.create_oval(x-3,y-3,x+3,y+3,fill='#f97316' if index in self.selected_vertices else '#e2e8f0',outline='')
    def _uv_points(self):
        w=max(1,self.uv_canvas.winfo_width());h=max(1,self.uv_canvas.winfo_height());size=min(w,h)*.84*self.uv_zoom;ox=w/2-size/2+self.uv_pan[0];oy=h/2-size/2+self.uv_pan[1];return [(ox+u*size,oy+(1-v)*size) for u,v in self.uvs]
    def draw_uv(self):
        c=self.uv_canvas;c.delete('all');c.create_rectangle(12,12,max(13,c.winfo_width()-12),max(13,c.winfo_height()-12),outline='#334155')
        if not self.uvs:return
        points=self._uv_points();mode=self.uv_mode.get()
        for face_id,face in enumerate(self.uv_faces):
            try:coords=[value for index in face for value in points[index]]
            except Exception:continue
            selected=face_id in self.selected_faces
            if len(coords)>=6:c.create_polygon(*coords,fill='#7c2d12' if selected else '#164e63' if mode=='Solid' else '',outline='#fb923c' if selected else '#67e8f9',width=2 if selected else 1)
        for edge in self.selected_edges:
            if edge[0]<len(points) and edge[1]<len(points):a,b=points[edge[0]],points[edge[1]];c.create_line(*a,*b,fill='#f97316',width=4)
        if mode=='Vertices':
            selected=self._selected_vertex_ids()
            for index,(x,y) in enumerate(points[:100000]):c.create_oval(x-2,y-2,x+2,y+2,fill='#f97316' if index in selected else '#e2e8f0',outline='')
    def export_png(self):
        if not self.uvs:return
        path=filedialog.asksaveasfilename(defaultextension='.png',filetypes=[('PNG','*.png')])
        if not path:return
        from PIL import Image,ImageDraw
        image=Image.new('RGBA',(2048,2048),(0,0,0,0));draw=ImageDraw.Draw(image);pts=[(int(u*2047),int((1-v)*2047)) for u,v in self.uvs]
        for face_id,face in enumerate(self.uv_faces):
            try:draw.line([pts[i] for i in face]+[pts[face[0]]],fill=(249,115,22,255) if face_id in self.selected_faces else (103,232,249,255),width=3 if face_id in self.selected_faces else 2)
            except Exception:pass
        image.save(path);self.status.set(f'Exported UV layout: {path}')
    def export_obj(self):
        if not self.vertices or not self.uvs:return
        path=filedialog.asksaveasfilename(defaultextension='.obj',filetypes=[('OBJ','*.obj')])
        if not path:return
        with open(path,'w',encoding='utf-8') as stream:
            for x,y,z in self.vertices:stream.write(f'v {x} {y} {z}\n')
            for u,v in self.uvs:stream.write(f'vt {u} {v}\n')
            for face_index,face in enumerate(self.faces):
                uv_face=self.uv_faces[face_index] if face_index<len(self.uv_faces) else face;stream.write('f '+' '.join(f'{vertex+1}/{uv_face[index]+1}' for index,vertex in enumerate(face))+'\n')
        self.status.set(f'Exported OBJ with UVs: {path}')

def build_uv_layout_tool(parent):return UVLayoutTool(parent)
