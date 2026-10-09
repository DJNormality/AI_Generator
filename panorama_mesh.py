"""Cubemap detection, assembly and local depth-to-mesh reconstruction."""
from __future__ import annotations
import math, os, re
from PIL import Image

TILE_RE=re.compile(r'(?:^|_)l(\d+)_([bdflru])_(\d+)_(\d+)(?:\s*\(\d+\))?\.(?:jpg|jpeg|png|webp)$',re.I)
FACE_NAMES={'f':'Front','b':'Back','l':'Left','r':'Right','u':'Up','d':'Down'}

def detect_cubemap(paths):
    hits=[]
    for path in paths:
        match=TILE_RE.search(os.path.basename(path))
        if match:hits.append((int(match.group(1)),match.group(2).lower(),int(match.group(3)),int(match.group(4)),path,'(' in os.path.basename(path)))
    if not hits:return None
    level=max(item[0] for item in hits);selected={}
    for item in hits:
        lev,face,row,col,path,duplicate=item
        if lev!=level:continue
        key=(face,row,col)
        if key not in selected or (selected[key][5] and not duplicate):selected[key]=item
    faces={}
    for face in 'fb lrud'.replace(' ',''):
        tiles=[item for key,item in selected.items() if key[0]==face]
        if not tiles:continue
        max_row=max(item[2] for item in tiles);max_col=max(item[3] for item in tiles);rows=[]
        for row in range(1,max_row+1):
            row_images=[]
            for col in range(1,max_col+1):
                item=selected.get((face,row,col))
                if item:row_images.append(Image.open(item[4]).convert('RGB'))
            if not row_images:continue
            height=max(image.height for image in row_images);width=sum(image.width for image in row_images);strip=Image.new('RGB',(width,height));x=0
            for image in row_images:strip.paste(image,(x,0));x+=image.width
            rows.append(strip)
        if rows:
            width=max(row.width for row in rows);height=sum(row.height for row in rows);canvas=Image.new('RGB',(width,height));y=0
            for row in rows:canvas.paste(row,(0,y));y+=row.height
            faces[face]=canvas
    return {'level':level,'faces':faces,'tile_count':len(selected)} if len(faces)>=4 else None

def load_depth_model(model_path):
    if not model_path or not os.path.isdir(model_path):raise RuntimeError('Select a local Depth Anything V2 model folder first.')
    try:
        import torch
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation
    except Exception as error:raise RuntimeError('Panorama depth requires torch and transformers. Run Setup or install transformers and safetensors.') from error
    processor=AutoImageProcessor.from_pretrained(model_path,local_files_only=True)
    model=AutoModelForDepthEstimation.from_pretrained(model_path,local_files_only=True)
    device='cuda' if torch.cuda.is_available() else 'cpu';model.to(device).eval()
    return processor,model,device

def infer_depth(image,bundle):
    import numpy as np, torch
    processor,model,device=bundle;inputs=processor(images=image,return_tensors='pt').to(device)
    with torch.inference_mode():prediction=model(**inputs).predicted_depth
    prediction=torch.nn.functional.interpolate(prediction.unsqueeze(1),size=(image.height,image.width),mode='bicubic',align_corners=False).squeeze()
    depth=prediction.detach().float().cpu().numpy();low,high=np.percentile(depth,[2,98]);depth=np.clip((depth-low)/max(high-low,1e-6),0,1)
    # Depth Anything may encode inverse-relative depth depending on checkpoint.
    # A bounded shell remains stable and rebuildable without claiming metric scale.
    return .65+depth*2.35

def _direction(face,u,v):
    if face=='f':point=(u,-v,1.)
    elif face=='b':point=(-u,-v,-1.)
    elif face=='r':point=(1.,-v,-u)
    elif face=='l':point=(-1.,-v,u)
    elif face=='u':point=(u,1.,v)
    else:point=(u,-1.,-v)
    length=math.sqrt(sum(value*value for value in point));return tuple(value/length for value in point)

def depth_faces_to_mesh(images,depth_maps,target_polygons,topology):
    import numpy as np
    face_count=max(1,len(images));factor=2 if topology=='Triangles' else 1
    grid=max(8,min(256,int(math.sqrt(target_polygons/max(1,face_count*factor)))+1));vertices=[];faces=[]
    for face,image in images.items():
        depth=depth_maps[face];base=len(vertices);height,width=depth.shape
        for row in range(grid):
            py=min(height-1,round(row*(height-1)/(grid-1)));v=-1.+2.*row/(grid-1)
            for col in range(grid):
                px=min(width-1,round(col*(width-1)/(grid-1)));u=-1.+2.*col/(grid-1);direction=_direction(face,u,v);radius=float(depth[py,px]);vertices.append(tuple(value*radius for value in direction))
        for row in range(grid-1):
            for col in range(grid-1):
                a=base+row*grid+col;b=a+1;c=base+(row+1)*grid+col+1;d=c-1
                if topology=='Triangles':faces.extend(((a,b,c),(a,c,d)))
                else:faces.append((a,b,c,d))
    return vertices,faces

def flat_sphere_depth(images):
    import numpy as np
    return {face:np.ones((image.height,image.width),dtype='float32') for face,image in images.items()}
