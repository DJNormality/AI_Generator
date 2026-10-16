"""Native glass chrome without chroma-key holes around raster controls."""
import ctypes as C,os

def apply_chrome(window,state):
 if os.name!='nt':return
 from aero_native import api,Accent,CompositionData,Margins,tint_value
 user,dwm,*_=api();hwnd=user.GetAncestor(window.winfo_id(),2)
 strength=float(state.get('blur_strength',55))/100
 # DWM draws glass only in chrome; editing surfaces keep their own opaque colors.
 margins=Margins(6,6,36,6) if state['enabled'] else Margins(0,0,0,0)
 dwm.DwmExtendFrameIntoClientArea(hwnd,C.byref(margins))
 fn=getattr(user,'SetWindowCompositionAttribute',None)
 if fn:
  fn.argtypes=[C.c_void_p,C.POINTER(CompositionData)];fn.restype=C.c_int
  enabled=state['enabled'] and state['blur'] and strength>0
  # Windows owns blur radius; the percentage mixes blur tint strength.
  opacity=round(255*(1-state['transparency']/100)*strength)
  accent=Accent(3 if enabled else 0,0,tint_value(state['color'],opacity),0)
  data=CompositionData(19,C.cast(C.pointer(accent),C.c_void_p),C.sizeof(accent));fn(hwnd,C.byref(data))
