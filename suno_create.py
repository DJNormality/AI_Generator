"""Suno song-planning workspace for AI Generator's Music > Create tab."""
from __future__ import annotations
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

SUNO_CREATE_URL='https://suno.com/create'
SUNO_PLATFORM_URL='https://platform.suno.com/'

class SunoCreateTool:
    def __init__(self,parent):
        self.parent=parent;self.title=tk.StringVar();self.style=tk.StringVar();self.instrumental=tk.BooleanVar(value=False)
        self.status=tk.StringVar(value='Prepare a song, copy it, then open the official Suno Create page.')
        self._build()
    def _build(self):
        root=ttk.Frame(self.parent,style='Panel.TFrame',padding=14);root.pack(fill='both',expand=True);root.columnconfigure(1,weight=1);root.rowconfigure(4,weight=1)
        ttk.Label(root,text='Suno Create',font=('Segoe UI Semibold',16)).grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,4))
        ttk.Label(root,text='Plan a song inside AI Generator, then send the prepared prompt to Suno. Your Suno sign-in remains in your browser and is never stored by AI Generator.',style='Hint.TLabel',wraplength=900,justify='left').grid(row=1,column=0,columnspan=3,sticky='ew',pady=(0,12))
        ttk.Label(root,text='Song title').grid(row=2,column=0,sticky='w',pady=4);ttk.Entry(root,textvariable=self.title).grid(row=2,column=1,sticky='ew',padx=8,pady=4);ttk.Checkbutton(root,text='Instrumental',variable=self.instrumental).grid(row=2,column=2,sticky='w',pady=4)
        ttk.Label(root,text='Style / genre').grid(row=3,column=0,sticky='w',pady=4);ttk.Entry(root,textvariable=self.style).grid(row=3,column=1,columnspan=2,sticky='ew',padx=(8,0),pady=4)
        editor=ttk.Panedwindow(root,orient='horizontal');editor.grid(row=4,column=0,columnspan=3,sticky='nsew',pady=(8,8));prompt_panel=ttk.Frame(editor,padding=(0,0,6,0));lyrics_panel=ttk.Frame(editor,padding=(6,0,0,0));editor.add(prompt_panel,weight=1);editor.add(lyrics_panel,weight=1)
        ttk.Label(prompt_panel,text='Song description / prompt').pack(anchor='w');self.prompt=tk.Text(prompt_panel,height=12,wrap='word',undo=True,bg='#0f172a',fg='#e2e8f0',insertbackground='#e2e8f0',selectbackground='#2563eb',relief='flat',padx=8,pady=8);self.prompt.pack(fill='both',expand=True,pady=(5,0))
        ttk.Label(lyrics_panel,text='Custom lyrics (optional)').pack(anchor='w');self.lyrics=tk.Text(lyrics_panel,height=12,wrap='word',undo=True,bg='#0f172a',fg='#e2e8f0',insertbackground='#e2e8f0',selectbackground='#2563eb',relief='flat',padx=8,pady=8);self.lyrics.pack(fill='both',expand=True,pady=(5,0))
        buttons=ttk.Frame(root);buttons.grid(row=5,column=0,columnspan=3,sticky='ew');ttk.Button(buttons,text='Copy Prompt',command=self.copy_prompt).pack(side='left');ttk.Button(buttons,text='Copy Full Song Setup',command=self.copy_full).pack(side='left',padx=6);ttk.Button(buttons,text='Open Suno Create',command=self.open_create).pack(side='left',padx=(8,6));ttk.Button(buttons,text='Suno API Platform',command=lambda:webbrowser.open(SUNO_PLATFORM_URL)).pack(side='left');ttk.Button(buttons,text='Clear',command=self.clear).pack(side='right')
        ttk.Label(root,textvariable=self.status,style='Hint.TLabel').grid(row=6,column=0,columnspan=3,sticky='w',pady=(8,0))
    def _prompt_text(self):
        parts=[self.prompt.get('1.0','end-1c').strip()];style=self.style.get().strip()
        if style:parts.append(f'Style: {style}')
        if self.instrumental.get():parts.append('Instrumental; no vocals')
        return '\n'.join(part for part in parts if part)
    def _full_text(self):
        parts=[];title=self.title.get().strip();prompt=self._prompt_text();lyrics=self.lyrics.get('1.0','end-1c').strip()
        if title:parts.append(f'Title: {title}')
        if prompt:parts.append(prompt)
        if lyrics and not self.instrumental.get():parts.append(f'Lyrics:\n{lyrics}')
        return '\n\n'.join(parts)
    def _copy(self,value,label):
        if not value:messagebox.showwarning('Suno Create','Enter a song description first.');return False
        self.parent.clipboard_clear();self.parent.clipboard_append(value);self.parent.update_idletasks();self.status.set(f'{label} copied. Paste it into Suno Create.');return True
    def copy_prompt(self):self._copy(self._prompt_text(),'Prompt')
    def copy_full(self):self._copy(self._full_text(),'Full song setup')
    def open_create(self):
        value=self._full_text()
        if value:self._copy(value,'Full song setup')
        webbrowser.open(SUNO_CREATE_URL);self.status.set('Suno Create opened in your browser. Paste the copied song setup there.')
    def clear(self):
        self.title.set('');self.style.set('');self.instrumental.set(False);self.prompt.delete('1.0','end');self.lyrics.delete('1.0','end');self.status.set('Create fields cleared.')

def build_suno_create(parent):return SunoCreateTool(parent)
