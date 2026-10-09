"""Client for a locally running ACE-Step 1.5 REST server."""
from __future__ import annotations
import json, os, time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

class AceStepError(RuntimeError):pass

def _request(base,path,payload=None,timeout=30):
    url=urljoin(base.rstrip('/')+'/',path.lstrip('/'));data=None;headers={'Accept':'application/json'}
    if payload is not None:data=json.dumps(payload).encode('utf-8');headers['Content-Type']='application/json'
    try:
        with urlopen(Request(url,data=data,headers=headers),timeout=timeout) as response:return json.loads(response.read().decode('utf-8'))
    except HTTPError as error:
        try:detail=error.read().decode('utf-8','replace')
        except Exception:detail=str(error)
        raise AceStepError(f'ACE-Step returned HTTP {error.code}: {detail[:500]}') from error
    except URLError as error:raise AceStepError(f'Cannot connect to ACE-Step at {base}. Start the local server first. ({error.reason})') from error

def _data(response):
    if not isinstance(response,dict):raise AceStepError('ACE-Step returned an invalid response.')
    if response.get('code',200)!=200 or response.get('error'):raise AceStepError(str(response.get('error') or response))
    return response.get('data')

def health(base):
    return _request(base,'/health',timeout=5)

def generate(base,output_dir,prompt,lyrics='',duration=60,bpm=None,key_scale='',time_signature='4',audio_format='wav',seed=-1,random_seed=True,inference_steps=8,model='acestep-v15-turbo',language='en',thinking=False,stop_event=None,progress=None):
    prompt=(prompt or '').strip();lyrics=(lyrics or '').strip()
    if not prompt:raise AceStepError('Enter a music description or style prompt.')
    payload={'prompt':prompt,'lyrics':lyrics,'task_type':'text2music','vocal_language':language or 'en','audio_format':audio_format,'audio_duration':max(10,min(600,float(duration))),'time_signature':str(time_signature or '4'),'inference_steps':max(1,min(20,int(inference_steps))),'batch_size':1,'model':model or 'acestep-v15-turbo','thinking':bool(thinking),'use_format':False,'use_cot_caption':False,'use_cot_language':False,'use_random_seed':bool(random_seed),'seed':-1 if random_seed else int(seed),'lm_backend':'pt','lm_model_path':'acestep-5Hz-lm-0.6B'}
    if bpm:payload['bpm']=max(30,min(300,int(bpm)))
    if key_scale:payload['key_scale']=key_scale.strip()
    if progress:progress(2,'Submitting track to the local ACE-Step server…')
    created=_data(_request(base,'/release_task',payload,60))
    task_id=created.get('task_id') if isinstance(created,dict) else created
    if not task_id:raise AceStepError('ACE-Step did not return a task ID.')
    percent=5
    while True:
        if stop_event and stop_event.is_set():raise AceStepError('Generation monitoring stopped. The local server may finish the current task in the background.')
        queried=_data(_request(base,'/query_result',{'task_id_list':[task_id]},30)) or []
        item=queried[0] if queried else {};status=int(item.get('status',0));percent=min(95,max(percent+1,int(float(item.get('progress',0) or 0)*100)))
        if progress:progress(percent,'ACE-Step is generating locally…')
        if status==2:raise AceStepError(str(item.get('error') or 'ACE-Step generation failed.'))
        if status==1:break
        time.sleep(2)
    result=item.get('result') or '[]'
    if isinstance(result,str):result=json.loads(result)
    if isinstance(result,dict):result=[result]
    if not result:raise AceStepError('ACE-Step completed without an audio result.')
    os.makedirs(output_dir,exist_ok=True);outputs=[]
    for number,entry in enumerate(result,1):
        remote=entry.get('file') if isinstance(entry,dict) else None
        if not remote:continue
        target=os.path.join(output_dir,f'ace_step_{task_id}_{number}.{audio_format}')
        if progress:progress(96,f'Downloading local result {number}…')
        try:
            with urlopen(urljoin(base.rstrip('/')+'/',remote.lstrip('/')),timeout=180) as source,open(target,'wb') as destination:
                while True:
                    block=source.read(1024*1024)
                    if not block:break
                    destination.write(block)
        except Exception as error:raise AceStepError(f'Could not save generated audio: {error}') from error
        if os.path.getsize(target)<100:raise AceStepError('ACE-Step returned an empty audio file.')
        outputs.append(target)
    if not outputs:raise AceStepError('ACE-Step returned no downloadable audio files.')
    if progress:progress(100,'Local track generation complete.')
    return outputs
