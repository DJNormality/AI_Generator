"""Minimal Tripo v3 text-to-model client with safe polling and immediate download."""
from __future__ import annotations
import os,time
import requests

BASE_URL='https://openapi.tripo3d.ai/v3'
FAILED_STATES={'failed','cancelled','banned'}

class TripoError(RuntimeError):pass

def _payload(response):
    try:data=response.json()
    except Exception as error:raise TripoError(f'Tripo returned HTTP {response.status_code} without valid JSON.') from error
    if response.status_code>=400 or data.get('code',0)!=0:
        message=data.get('message') or data.get('data') or data
        raise TripoError(f'Tripo API error: {message}')
    return data.get('data') or {}

def text_to_model(prompt,api_key,output_path,model='v3.1-20260211',face_limit=20000,progress=None):
    prompt=(prompt or '').strip();api_key=(api_key or '').strip()
    if not prompt:raise TripoError('Enter a text-to-model prompt.')
    if not api_key:raise TripoError('Set TRIPO_API_KEY or enter the Tripo API key for this session.')
    headers={'Authorization':f'Bearer {api_key}','Content-Type':'application/json','User-Agent':'AI-Generator/1.0'}
    body={'prompt':prompt,'model':model}
    if face_limit:body['face_limit']=max(100,int(face_limit))
    if progress:progress(2,'Submitting Tripo text-to-model task...')
    response=requests.post(f'{BASE_URL}/generation/text-to-model',headers=headers,json=body,timeout=60)
    task_id=_payload(response).get('task_id')
    if not task_id:raise TripoError('Tripo did not return a task ID.')
    if progress:progress(5,f'Tripo task created: {task_id}')
    while True:
        task=_payload(requests.get(f'{BASE_URL}/tasks/{task_id}',headers={'Authorization':f'Bearer {api_key}','User-Agent':'AI-Generator/1.0'},timeout=30))
        status=str(task.get('status','')).lower();amount=max(0,min(100,int(task.get('progress') or 0)))
        if progress:progress(max(5,min(95,amount)),f'Tripo: {status or "working"} — {amount}%')
        if status=='success':break
        if status in FAILED_STATES:raise TripoError(f'Tripo generation ended with status: {status}.')
        time.sleep(2)
    output=task.get('output') or {};model_url=output.get('model_url')
    if not model_url:raise TripoError('Tripo completed but returned no model URL.')
    if progress:progress(96,'Downloading the completed GLB before its link expires...')
    download=requests.get(model_url,timeout=180);download.raise_for_status();os.makedirs(os.path.dirname(output_path),exist_ok=True)
    with open(output_path,'wb') as stream:
        for block in download.iter_content(1024*1024):
            if block:stream.write(block)
    if os.path.getsize(output_path)<100:raise TripoError('The downloaded GLB is empty or incomplete.')
    if progress:progress(100,'Tripo model downloaded.')
    return {'task_id':task_id,'path':output_path,'rendered_image_url':output.get('rendered_image_url')}
