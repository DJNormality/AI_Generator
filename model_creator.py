"""Local multi-image silhouette mesh builder for Models > Create."""
from __future__ import annotations
import hashlib, json, math, os, shutil, subprocess, threading
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageChops, ImageStat
from extract_preview3d import ExtractPreview3D
from panorama_mesh import detect_cubemap, depth_faces_to_mesh, flat_sphere_depth, infer_depth, load_depth_model

IMAGE_TYPES=('.png','.jpg','.jpeg','.webp','.bmp','.tif','.tiff')

class MeshCreator:
    def __init__(self,parent):
        self.parent=parent;self.project_dir='';self.sources=[];self.vertices=[];self.faces=[];self.generation=0;self.busy=False
        self.status_var=tk.StringVar(value='Add multiple views of one object to begin.')
        self.poly_target=tk.IntVar(value=20000);self.topology=tk.StringVar(value='Quads');self.progress=tk.DoubleVar(value=0)
        self.engine=tk.StringVar(value='Auto detect');self.depth_model_path=tk.StringVar(value=self._saved_tool_path('depth_model_location.txt'));self.colmap_path=tk.StringVar(value=self._saved_tool_path('colmap_location.txt'));self.video_interval=tk.DoubleVar(value=1.0)
        self.local_3d_texture=tk.IntVar(value=1024);self.local_3d_remesh=tk.StringVar(value='triangle');self.last_glb=''
        self._build_ui()
    @staticmethod
    def _saved_tool_path(filename):
        path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'tools',filename)
        try:
            with open(path,'r',encoding='utf-8-sig') as stream:value=stream.readline().strip().strip('"')
            return value if os.path.exists(value) else ''
        except Exception:return ''
    def _build_ui(self):
        root=ttk.Frame(self.parent,style='Panel.TFrame',padding=10);root.pack(fill='both',expand=True)
        bar=ttk.Frame(root);bar.pack(fill='x',pady=(0,8))
        for text,command in (('Add Images',self.add_images),('Add Folder',self.add_folder),('Add Video',self.add_video),('Clear',self.clear),('Index Images',self.index_images)):
            ttk.Button(bar,text=text,command=command).pack(side='left',padx=(0,5))
        self.build_button=ttk.Button(bar,text='Build Mesh',command=self.build_mesh);self.build_button.pack(side='left',padx=(7,5))
        self.rebuild_button=ttk.Button(bar,text='Rebuild Mesh',command=lambda:self.build_mesh(True));self.rebuild_button.pack(side='left')
        ttk.Button(bar,text='Export OBJ',command=self.export_obj).pack(side='left',padx=(7,0))
        ttk.Button(bar,text='Export GLB',command=self.export_glb).pack(side='left',padx=(5,0))
        ttk.Button(bar,text='Install Local 3D',command=self.install_local_3d).pack(side='left',padx=(5,0))
        settings=ttk.Frame(root);settings.pack(fill='x',pady=(0,8))
        ttk.Label(settings,text='Target polygons').pack(side='left');ttk.Spinbox(settings,from_=100,to=1000000,increment=100,textvariable=self.poly_target,width=11).pack(side='left',padx=(5,14))
        ttk.Label(settings,text='Final topology').pack(side='left');ttk.Combobox(settings,textvariable=self.topology,values=('Quads','Triangles'),state='readonly',width=11).pack(side='left',padx=5)
        ttk.Label(settings,text='Engine').pack(side='left',padx=(12,3));ttk.Combobox(settings,textvariable=self.engine,values=('Auto detect','Local AI 3D (SF3D)','Panorama depth','Photogrammetry (COLMAP)','Silhouette'),state='readonly',width=23).pack(side='left')
        model_row=ttk.Frame(root);model_row.pack(fill='x',pady=(0,4));ttk.Label(model_row,text='Local depth model').pack(side='left');ttk.Entry(model_row,textvariable=self.depth_model_path).pack(side='left',fill='x',expand=True,padx=5);ttk.Button(model_row,text='Browse',command=self.choose_depth_model).pack(side='left');ttk.Label(model_row,text='Video interval').pack(side='left',padx=(12,3));ttk.Spinbox(model_row,from_=.1,to=30,increment=.1,textvariable=self.video_interval,width=6).pack(side='left');ttk.Label(model_row,text='seconds').pack(side='left')
        colmap_row=ttk.Frame(root);colmap_row.pack(fill='x',pady=(0,8));ttk.Label(colmap_row,text='COLMAP executable').pack(side='left');ttk.Entry(colmap_row,textvariable=self.colmap_path).pack(side='left',fill='x',expand=True,padx=5);ttk.Button(colmap_row,text='Browse',command=self.choose_colmap).pack(side='left')
        local_row=ttk.Frame(root);local_row.pack(fill='x',pady=(0,8));ttk.Label(local_row,text='Local AI 3D uses the first source image and creates a textured UV-unwrapped GLB.').pack(side='left');ttk.Label(local_row,text='Texture').pack(side='left',padx=(18,3));ttk.Combobox(local_row,textvariable=self.local_3d_texture,values=(512,1024,2048),state='readonly',width=7).pack(side='left');ttk.Label(local_row,text='Remesh').pack(side='left',padx=(12,3));ttk.Combobox(local_row,textvariable=self.local_3d_remesh,values=('none','triangle','quad'),state='readonly',width=9).pack(side='left')
        body=ttk.Panedwindow(root,orient='horizontal');body.pack(fill='both',expand=True)
        left=ttk.Frame(body,padding=(0,0,8,0));right=ttk.Frame(body);body.add(left,weight=0);body.add(right,weight=1)
        ttk.Label(left,text='Source image index').pack(anchor='w');box=ttk.Frame(left);box.pack(fill='both',expand=True,pady=(5,0))
        self.listbox=tk.Listbox(box,width=42,bg='#0f172a',fg='#e2e8f0',selectbackground='#2563eb',exportselection=False);scroll=ttk.Scrollbar(box,command=self.listbox.yview);self.listbox.configure(yscrollcommand=scroll.set);self.listbox.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        self.viewer=ExtractPreview3D(right,self.set_status)
        footer=ttk.Frame(root);footer.pack(fill='x',pady=(8,0));ttk.Progressbar(footer,variable=self.progress,maximum=100,style='Accent.Horizontal.TProgressbar').pack(side='left',fill='x',expand=True);ttk.Label(footer,textvariable=self.status_var).pack(side='left',padx=(10,0))
    def set_status(self,text):self.status_var.set(text)
    def add_images(self):
        self._add(filedialog.askopenfilenames(title='Select source views',filetypes=[('Images',' '.join('*'+ext for ext in IMAGE_TYPES)),('All files','*.*')]))
    def add_folder(self):
        folder=filedialog.askdirectory(title='Select source-image folder')
        if folder:self._add(os.path.join(folder,name) for name in sorted(os.listdir(folder)) if os.path.splitext(name)[1].lower() in IMAGE_TYPES)
    def choose_depth_model(self):
        folder=filedialog.askdirectory(title='Select local Depth Anything V2 model folder')
        if folder:self.depth_model_path.set(folder)
    def choose_colmap(self):
        path=filedialog.askopenfilename(title='Select COLMAP.exe or COLMAP.bat',filetypes=[('COLMAP launcher','*.exe *.bat *.cmd'),('All files','*.*')])
        if path:self.colmap_path.set(path)
    def install_local_3d(self):
        script=os.path.join(os.path.dirname(os.path.abspath(__file__)),'Setup_Local_3D_Generator.bat')
        if not os.path.isfile(script):messagebox.showerror('Local AI 3D','Setup_Local_3D_Generator.bat is missing.');return
        try:os.startfile(script)
        except Exception as error:messagebox.showerror('Local AI 3D',str(error))
    def add_video(self):
        path=filedialog.askopenfilename(title='Select moving-camera video',filetypes=[('Video','*.mp4 *.mov *.mkv *.avi *.webm'),('All files','*.*')])
        if not path:return
        output=filedialog.askdirectory(title='Choose folder for extracted video frames')
        if not output:return
        try:
            import cv2
            capture=cv2.VideoCapture(path);fps=capture.get(cv2.CAP_PROP_FPS) or 30.;step=max(1,round(fps*max(.1,float(self.video_interval.get()))));frame=0;saved=0;last=None
            while True:
                ok,image=capture.read()
                if not ok:break
                if frame%step==0:
                    gray=cv2.resize(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),(64,64));keep=last is None or float(cv2.absdiff(gray,last).mean())>2.0
                    if keep:
                        target=os.path.join(output,f'frame_{saved:06d}.jpg');cv2.imwrite(target,image,[cv2.IMWRITE_JPEG_QUALITY,95]);self._add((target,));saved+=1;last=gray
                frame+=1
            capture.release();self.set_status(f'Extracted {saved} distinct moving-camera frames. Use Photogrammetry (COLMAP).')
        except Exception as error:messagebox.showerror('Video Frames',f'Could not extract video frames: {error}')
    def _add(self,paths):
        known={os.path.normcase(os.path.abspath(path)) for path in self.sources}
        for path in paths:
            full=os.path.abspath(path)
            if os.path.isfile(full) and os.path.normcase(full) not in known:self.sources.append(full);known.add(os.path.normcase(full));self.listbox.insert('end',os.path.basename(full))
        self.set_status(f'{len(self.sources)} source image(s) selected.')
    def clear(self):
        if self.busy:return
        self.sources.clear();self.vertices.clear();self.faces.clear();self.generation=0;self.project_dir='';self.listbox.delete(0,'end');self.viewer.set_geometry([],[]);self.progress.set(0);self.set_status('Source list cleared.')
    @staticmethod
    def _digest(path):
        digest=hashlib.sha256()
        with open(path,'rb') as stream:
            for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
        return digest.hexdigest()
    def index_images(self):
        if not self.sources:messagebox.showerror('Create Mesh','Add source images first.');return False
        folder=filedialog.askdirectory(title='Choose or create a mesh project folder')
        if not folder:return False
        self.project_dir=os.path.abspath(folder);image_dir=os.path.join(self.project_dir,'images');os.makedirs(image_dir,exist_ok=True);os.makedirs(os.path.join(self.project_dir,'generations'),exist_ok=True);indexed=[]
        for number,source in enumerate(self.sources,1):
            stem,ext=os.path.splitext(os.path.basename(source));target=os.path.join(image_dir,f'{number:04d}_{stem}{ext.lower()}');shutil.copy2(source,target)
            with Image.open(target) as image:size=list(image.size)
            indexed.append({'file':os.path.relpath(target,self.project_dir),'original':source,'sha256':self._digest(target),'size':size})
        manifest={'format':1,'created':datetime.now().isoformat(timespec='seconds'),'generation':0,'images':indexed,'history':[]}
        with open(os.path.join(self.project_dir,'mesh_index.json'),'w',encoding='utf-8') as stream:json.dump(manifest,stream,indent=2)
        self.sources=[os.path.join(self.project_dir,item['file']) for item in indexed];self.set_status(f'Indexed {len(indexed)} image(s) in {self.project_dir}.');return True
    def build_mesh(self,rebuild=False):
        if self.busy:return
        selected_engine=self.engine.get()
        if not self.sources:messagebox.showerror('Create Mesh','Add at least one source image. Multiple angles work better.');return
        if not self.project_dir and not self.index_images():return
        try:target=max(100,min(1000000,int(self.poly_target.get())))
        except Exception:messagebox.showerror('Create Mesh','Enter a valid polygon target.');return
        self.busy=True;self.progress.set(1);self.build_button.configure(state='disabled');self.rebuild_button.configure(state='disabled');generation=self.generation+1 if rebuild or self.generation else 1
        threading.Thread(target=self._build_worker,args=(target,generation,self.topology.get(),self.engine.get()),daemon=True).start()
    def _build_worker(self,target,generation,topology,engine):
        try:
            cubemap=detect_cubemap(self.sources)
            chosen=engine
            if chosen=='Auto detect':chosen='Panorama depth' if cubemap else 'Silhouette'
            if chosen=='Local AI 3D (SF3D)':
                self._run_local_3d(generation,target);return
            if chosen=='Panorama depth':
                if not cubemap:raise RuntimeError('These filenames do not form a recognized cubemap panorama. Select Auto detect, Photogrammetry, or Silhouette.')
                images=cubemap['faces'];model_path=self.depth_model_path.get().strip()
                if model_path:
                    bundle=load_depth_model(model_path);depth_maps={}
                    for number,(face,image) in enumerate(images.items(),1):depth_maps[face]=infer_depth(image,bundle);self.parent.after(0,self.progress.set,number/max(1,len(images))*75)
                    method='Depth Anything V2 panorama depth'
                else:
                    depth_maps=flat_sphere_depth(images);method='cubemap sphere preview (select a Depth Anything V2 folder for estimated interior depth)'
                vertices,faces=depth_faces_to_mesh(images,depth_maps,target,topology);out=os.path.join(self.project_dir,'generations',f'mesh_generation_{generation:03d}.obj');self._write_obj(out,vertices,faces,generation);self._update_manifest(out,generation,len(vertices),len(faces),target,topology,method);self.parent.after(0,self._finish_build,vertices,faces,generation,out);return
            if chosen=='Photogrammetry (COLMAP)':
                if cubemap:raise RuntimeError('This source is a single-position cubemap panorama, not moving-camera photographs. Use Panorama depth. COLMAP cannot triangulate real depth without camera translation/parallax.')
                self._run_colmap(target,generation,topology);return
            profiles=[]
            for number,path in enumerate(self.sources,1):profiles.append(self._profile(path,generation));self.parent.after(0,self.progress.set,number/max(1,len(self.sources))*45)
            face_factor=2 if topology=='Triangles' else 1
            rows=max(8,min(512,int(math.sqrt(target/max(1,face_factor)))));segments=max(8,min(512,target//max(1,(rows-1)*face_factor)));profile=self._combine_profiles(profiles,rows,generation);vertices,faces=self._revolve(profile,segments,topology)
            out=os.path.join(self.project_dir,'generations',f'mesh_generation_{generation:03d}.obj');self._write_obj(out,vertices,faces,generation);self._update_manifest(out,generation,len(vertices),len(faces),target,topology,'silhouette profile');self.parent.after(0,self._finish_build,vertices,faces,generation,out)
        except Exception as error:self.parent.after(0,self._fail_build,str(error))
    @staticmethod
    def _profile(path,generation):
        with Image.open(path) as source:image=source.convert('RGBA')
        image.thumbnail((768,768),Image.Resampling.LANCZOS);alpha=image.getchannel('A')
        if alpha.getextrema()[0]<250:mask=alpha.point(lambda value:255 if value>12 else 0)
        else:
            rgb=image.convert('RGB');w,h=rgb.size;corners=[rgb.getpixel((0,0)),rgb.getpixel((w-1,0)),rgb.getpixel((0,h-1)),rgb.getpixel((w-1,h-1))];bg=tuple(sum(pixel[c] for pixel in corners)//4 for c in range(3));difference=ImageChops.difference(rgb,Image.new('RGB',rgb.size,bg)).convert('L');spread=ImageStat.Stat(difference).rms[0];threshold=max(10,min(80,int(spread*(.50-min(generation,8)*.018))));mask=difference.point(lambda value:255 if value>threshold else 0)
        bounds=mask.getbbox()
        if not bounds:raise ValueError(f'No foreground silhouette found in {os.path.basename(path)}.')
        mask=mask.crop(bounds);pixels=mask.load();widths=[]
        for y in range(mask.height):
            active=[x for x in range(mask.width) if pixels[x,y]>0];widths.append((max(active)-min(active)+1)/max(1,mask.width) if active else 0.)
        return widths
    @staticmethod
    def _combine_profiles(profiles,rows,generation):
        sampled=[[profile[min(len(profile)-1,round(index*(len(profile)-1)/(rows-1)))] for index in range(rows)] for profile in profiles];values=[sum(profile[index] for profile in sampled)/len(sampled) for index in range(rows)]
        for _ in range(min(8,2+generation)):values=[values[0]]+[(values[i-1]+values[i]*2+values[i+1])/4 for i in range(1,rows-1)]+[values[-1]]
        peak=max(values) or 1.;return [max(.012,value/peak) for value in values]
    @staticmethod
    def _revolve(profile,segments,topology):
        vertices=[];faces=[];rows=len(profile)
        for row,radius in enumerate(profile):
            y=1.-2.*row/max(1,rows-1)
            for segment in range(segments):angle=2*math.pi*segment/segments;vertices.append((radius*math.cos(angle),y,radius*math.sin(angle)))
        for row in range(rows-1):
            for segment in range(segments):
                nxt=(segment+1)%segments;a=row*segments+segment;b=row*segments+nxt;c=(row+1)*segments+nxt;d=(row+1)*segments+segment
                if topology=='Triangles':faces.extend(((a,b,c),(a,c,d)))
                else:faces.append((a,b,c,d))
        return vertices,faces
    @staticmethod
    def _write_obj(path,vertices,faces,generation):
        with open(path,'w',encoding='utf-8',newline='\n') as stream:
            stream.write(f'# AI Generator image mesh - generation {generation}\n')
            for x,y,z in vertices:stream.write(f'v {x:.8f} {y:.8f} {z:.8f}\n')
            for face in faces:stream.write('f '+' '.join(str(index+1) for index in face)+'\n')
    def _run_colmap(self,target,generation,topology):
        executable=self.colmap_path.get().strip() or shutil.which('colmap') or shutil.which('colmap.exe')
        if not executable or not os.path.isfile(executable):raise RuntimeError('Select colmap.exe first. COLMAP is required for moving-camera photos or video.')
        workspace=os.path.join(self.project_dir,'colmap',f'generation_{generation:03d}');image_dir=os.path.join(workspace,'input_images');os.makedirs(image_dir,exist_ok=True)
        valid=0;skipped=0
        for number,source in enumerate(self.sources,1):
            if os.path.splitext(source)[1].lower() not in IMAGE_TYPES:skipped+=1;continue
            try:
                with Image.open(source) as probe:probe.verify()
                stem,ext=os.path.splitext(os.path.basename(source));target_path=os.path.join(image_dir,f'{number:06d}_{stem}{ext.lower()}');shutil.copy2(source,target_path);valid+=1
            except Exception:skipped+=1
        if valid<2:raise RuntimeError('COLMAP needs at least two readable moving-camera images. No JSON, OBJ, cache, or index files are accepted.')
        self.parent.after(0,self.set_status,f'COLMAP received {valid} verified images ({skipped} non-images skipped). Matching cameras and building dense geometry...')
        arguments=['automatic_reconstructor','--workspace_path',workspace,'--image_path',image_dir,'--data_type','VIDEO','--quality','MEDIUM','--use_gpu','1']
        command=(['cmd','/c',executable]+arguments) if os.path.splitext(executable)[1].lower() in ('.bat','.cmd') else [executable]+arguments
        environment=os.environ.copy();exe_dir=os.path.dirname(os.path.abspath(executable));install_dir=os.path.dirname(exe_dir)
        path_folders=[exe_dir,os.path.join(install_dir,'bin'),os.path.join(install_dir,'lib')]
        environment['PATH']=os.pathsep.join([folder for folder in path_folders if os.path.isdir(folder)]+[environment.get('PATH','')])
        platform_candidates=[os.path.join(exe_dir,'platforms'),os.path.join(install_dir,'platforms'),os.path.join(install_dir,'plugins','platforms'),os.path.join(install_dir,'lib','plugins','platforms'),os.path.join(install_dir,'share','qt','plugins','platforms')]
        platform_dir=next((folder for folder in platform_candidates if os.path.isfile(os.path.join(folder,'qwindows.dll'))),None)
        if platform_dir:
            environment['QT_QPA_PLATFORM_PLUGIN_PATH']=platform_dir;environment['QT_PLUGIN_PATH']=os.path.dirname(platform_dir)
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
        result=subprocess.run(command,capture_output=True,text=True,env=environment,creationflags=flags)
        candidates=[]
        for root,_dirs,names in os.walk(workspace):
            for name in names:
                if name.lower() in ('meshed-poisson.ply','meshed-delaunay.ply','fused.ply'):candidates.append(os.path.join(root,name))
        if not candidates:
            detail=(result.stderr or result.stdout)[-1200:] if result.returncode else ''
            if 'qt.qpa.plugin' in detail.lower() or 'qwindows' in detail.lower():
                raise RuntimeError('COLMAP could not find its Qt Windows plugin. Select COLMAP.bat from the top-level COLMAP folder, or reinstall the complete Windows COLMAP package so plugins\\platforms\\qwindows.dll is present. Do not copy colmap.exe by itself.')
            raise RuntimeError('COLMAP did not produce a dense PLY mesh. The images may lack camera movement, overlap, or trackable detail. '+detail)
        source=next((path for path in candidates if 'meshed-' in os.path.basename(path).lower()),candidates[0])
        try:import trimesh
        except Exception as error:raise RuntimeError('Install trimesh to convert the COLMAP PLY result to OBJ: pip install trimesh') from error
        mesh=trimesh.load(source,force='mesh',process=False)
        if not hasattr(mesh,'vertices') or len(mesh.vertices)<3:raise RuntimeError('COLMAP output contains no usable mesh vertices.')
        if not hasattr(mesh,'faces') or len(mesh.faces)<1:raise RuntimeError('COLMAP produced a point cloud but no surface mesh. More moving-camera overlap is required.')
        out=os.path.join(self.project_dir,'generations',f'mesh_generation_{generation:03d}.obj');mesh.export(out,file_type='obj');vertices=[tuple(map(float,row)) for row in mesh.vertices];faces=[tuple(map(int,row)) for row in mesh.faces]
        self._update_manifest(out,generation,len(vertices),len(faces),target,'Triangles','COLMAP moving-camera photogrammetry');self.parent.after(0,self._finish_build,vertices,faces,generation,out)
    def _run_local_3d(self,generation,target):
        app_dir=os.path.dirname(os.path.abspath(__file__));repo=os.path.join(app_dir,'tools','stable-fast-3d');python=os.path.join(repo,'.venv','Scripts','python.exe');runner=os.path.join(repo,'run.py')
        if not os.path.isfile(python) or not os.path.isfile(runner):raise RuntimeError('Local AI 3D is not installed. Run Setup_Local_3D_Generator.bat first.')
        source=self.sources[0];work=os.path.join(self.project_dir,'local_3d',f'generation_{generation:03d}');os.makedirs(work,exist_ok=True)
        self.parent.after(0,self.set_status,'Local AI 3D is reconstructing and texturing the first source image…');self.parent.after(0,self.progress.set,10)
        command=[python,runner,source,'--output-dir',work,'--texture-resolution',str(self.local_3d_texture.get()),'--remesh_option',self.local_3d_remesh.get()]
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0);result=subprocess.run(command,cwd=repo,capture_output=True,text=True,creationflags=flags)
        candidates=[]
        for folder,_dirs,names in os.walk(work):
            candidates.extend(os.path.join(folder,name) for name in names if name.lower().endswith('.glb'))
        if result.returncode or not candidates:raise RuntimeError('Local AI 3D did not create a GLB. '+(result.stderr or result.stdout)[-1400:])
        source_glb=max(candidates,key=os.path.getmtime);out=os.path.join(self.project_dir,'generations',f'local_ai_3d_generation_{generation:03d}.glb');shutil.copy2(source_glb,out);self.parent.after(0,self.progress.set,88)
        try:
            import trimesh
            loaded=trimesh.load(out,force='scene',process=False)
            if isinstance(loaded,trimesh.Scene):
                mesh=loaded.dump(concatenate=True)
            else:mesh=loaded
            if mesh is None or len(mesh.vertices)<3 or len(mesh.faces)<1:raise RuntimeError('The GLB contains no previewable triangle mesh.')
            vertices=[tuple(map(float,row)) for row in mesh.vertices];faces=[tuple(map(int,row)) for row in mesh.faces]
        except Exception as error:raise RuntimeError(f'The local GLB was created, but its preview could not be loaded: {error}') from error
        self.last_glb=out;self._update_manifest(out,generation,len(vertices),len(faces),target,'Triangles','Local AI 3D (Stable Fast 3D)');self.parent.after(0,self._finish_build,vertices,faces,generation,out)
    def _update_manifest(self,obj_path,generation,vertices,faces,target,topology,method='unknown'):
        path=os.path.join(self.project_dir,'mesh_index.json')
        with open(path,'r',encoding='utf-8') as stream:manifest=json.load(stream)
        manifest['generation']=generation;manifest.setdefault('history',[]).append({'generation':generation,'created':datetime.now().isoformat(timespec='seconds'),'obj':os.path.relpath(obj_path,self.project_dir),'vertices':vertices,'faces':faces,'target_polygons':target,'topology':topology,'method':method})
        with open(path,'w',encoding='utf-8') as stream:json.dump(manifest,stream,indent=2)
    def _finish_build(self,vertices,faces,generation,path):
        self.vertices,self.faces,self.generation=vertices,faces,generation;self.viewer.set_geometry(vertices,faces);self.progress.set(100);self.busy=False;self.build_button.configure(state='normal');self.rebuild_button.configure(state='normal');self.set_status(f'Generation {generation}: {len(vertices):,} vertices, {len(faces):,} faces. Saved {os.path.basename(path)}.')
    def _fail_build(self,error):
        self.busy=False;self.build_button.configure(state='normal');self.rebuild_button.configure(state='normal');self.progress.set(0);self.set_status(f'Build failed: {error}');messagebox.showerror('Create Mesh',error)
    def export_obj(self):
        if not self.vertices:messagebox.showerror('Export OBJ','Build a mesh first.');return
        path=filedialog.asksaveasfilename(title='Export mesh',defaultextension='.obj',filetypes=[('Wavefront OBJ','*.obj')])
        if path:self._write_obj(path,self.vertices,self.faces,self.generation);self.set_status(f'Exported {path}.')
    def export_glb(self):
        if not self.last_glb or not os.path.isfile(self.last_glb):messagebox.showerror('Export GLB','Generate a local AI 3D model first.');return
        path=filedialog.asksaveasfilename(title='Export textured local model',defaultextension='.glb',initialfile=os.path.basename(self.last_glb),filetypes=[('Binary glTF','*.glb')])
        if path:shutil.copy2(self.last_glb,path);self.set_status(f'Exported {path}.')

def build_model_creator(parent):return MeshCreator(parent)
