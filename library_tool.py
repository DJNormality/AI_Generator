"""Online reference Library embedded in AI Generator."""
import html
import os
import re
import shutil
import subprocess
import threading
import tkinter as tk
import urllib.parse
import webbrowser
import xml.etree.ElementTree as ET
from tkinter import messagebox, ttk

import requests


CATEGORIES = ('Games', 'Movies', 'Sports', 'TV', 'Stream', 'Music', 'Nature',
              'Companies', 'Jobs', 'Crypto', 'Stocks', 'Gas')
MODES = ('Tutorials', 'Instructions', 'Configurations', 'Research')


class LibraryTool:
    def __init__(self, parent):
        self.parent = parent
        self.online = False
        self.results = {mode: [] for mode in MODES}
        self.category = tk.StringVar(value='Games')
        self.query = tk.StringVar()
        self.browser = tk.StringVar(value='Google / Default')
        self.connection = tk.StringVar(value='Checking connection...')
        self.status = tk.StringVar(value='Ready')
        self._build()
        self.check_connection()

    def _build(self):
        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_rowconfigure(2, weight=1)
        title = ttk.Frame(self.parent, padding=(8, 4))
        title.grid(row=0, column=0, sticky='ew')
        ttk.Label(title, text='Online Information Library',
                  font=('Segoe UI Semibold', 14)).pack(side='left')
        ttk.Label(title, textvariable=self.connection).pack(side='right')

        controls = ttk.Frame(self.parent, padding=(8, 4))
        controls.grid(row=1, column=0, sticky='ew')
        controls.grid_columnconfigure(3, weight=1)
        ttk.Label(controls, text='Category').grid(row=0, column=0, sticky='w')
        ttk.Combobox(controls, textvariable=self.category, values=CATEGORIES,
                     state='readonly', width=14).grid(row=0, column=1, padx=(6, 14))
        ttk.Label(controls, text='Search').grid(row=0, column=2, sticky='w')
        entry = ttk.Entry(controls, textvariable=self.query)
        entry.grid(row=0, column=3, sticky='ew', padx=6)
        entry.bind('<Return>', lambda _event: self.search())
        self.search_button = ttk.Button(controls, text='Search Library', command=self.search)
        self.search_button.grid(row=0, column=4, padx=(0, 6))
        ttk.Label(controls, text='Browser').grid(row=0, column=5, sticky='w')
        ttk.Combobox(controls, textvariable=self.browser,
                     values=('Google / Default', 'Microsoft Edge', 'Firefox',
                             'Safari', 'All installed browsers'),
                     state='readonly', width=21).grid(row=0, column=6, padx=6)
        self.browser_button = ttk.Button(controls, text='Search Web', command=self.search_browser)
        self.browser_button.grid(row=0, column=7)

        self.notebook = ttk.Notebook(self.parent)
        self.notebook.grid(row=2, column=0, sticky='nsew', padx=8, pady=4)
        self.views = {}
        for mode in MODES:
            tab = ttk.Frame(self.notebook, padding=5)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=3)
            tab.grid_rowconfigure(1, weight=2)
            tree = ttk.Treeview(tab, columns=('title', 'source'), show='headings')
            tree.heading('title', text=f'{mode} results')
            tree.heading('source', text='Source')
            tree.column('title', width=650, anchor='w')
            tree.column('source', width=150, anchor='w')
            scroll = ttk.Scrollbar(tab, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scroll.set)
            tree.grid(row=0, column=0, sticky='nsew')
            scroll.grid(row=0, column=1, sticky='ns')
            details = tk.Text(tab, bg='#0f172a', fg='#e5e7eb', insertbackground='white',
                              wrap='word', height=8, relief='flat', padx=9, pady=7)
            details.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=(5, 0))
            details.config(state='disabled')
            tree.bind('<<TreeviewSelect>>', lambda _event, m=mode: self.show_details(m))
            tree.bind('<Double-1>', lambda _event, m=mode: self.open_selected(m))
            self.notebook.add(tab, text=f'  {mode.upper()}  ')
            self.views[mode] = (tree, details)

        bottom = ttk.Frame(self.parent, padding=(8, 3, 8, 7))
        bottom.grid(row=3, column=0, sticky='ew')
        ttk.Label(bottom, textvariable=self.status).pack(side='left')
        ttk.Button(bottom, text='Open Selected', command=self.open_current).pack(side='right')
        ttk.Button(bottom, text='Check Connection', command=self.check_connection).pack(
            side='right', padx=(0, 6))

    def check_connection(self):
        self.connection.set('Checking connection...')
        self.search_button.config(state='disabled')
        self.browser_button.config(state='disabled')
        def worker():
            connected = False
            for url in ('https://www.google.com/generate_204', 'https://en.wikipedia.org/'):
                try:
                    response = requests.get(url, timeout=4, stream=True,
                                            headers={'User-Agent': 'AI-Generator-Library/1.0'})
                    connected = response.status_code < 500
                    response.close()
                    if connected:
                        break
                except requests.RequestException:
                    pass
            self.parent.after(0, lambda: self._set_connection(connected))
        threading.Thread(target=worker, daemon=True).start()

    def _set_connection(self, connected):
        self.online = connected
        self.connection.set('Connected' if connected else 'Not Connected')
        self.status.set('Ready for online search' if connected else 'Not Connected')
        state = 'normal' if connected else 'disabled'
        self.search_button.config(state=state)
        self.browser_button.config(state=state)

    def search(self):
        if not self.online:
            self.status.set('Not Connected')
            return
        topic = self.query.get().strip() or self.category.get()
        category = self.category.get()
        self.status.set(f'Searching {category}: {topic}...')
        self.search_button.config(state='disabled')
        def worker():
            for mode in MODES:
                try:
                    self.results[mode] = self._collect(topic, category, mode)
                except Exception as error:
                    self.results[mode] = [{'title': f'Search error: {error}', 'source': 'Error',
                                           'url': '', 'summary': str(error)}]
            self.parent.after(0, self._finish_search)
        threading.Thread(target=worker, daemon=True).start()

    def _collect(self, topic, category, mode):
        phrase = f'{topic} {category} {mode[:-1].lower()}'
        rows = []
        headers = {'User-Agent': 'AI-Generator-Library/1.0'}
        wiki = requests.get('https://en.wikipedia.org/w/api.php', timeout=8, headers=headers,
                            params={'action': 'query', 'list': 'search', 'srsearch': phrase,
                                    'utf8': 1, 'format': 'json', 'srlimit': 8})
        wiki.raise_for_status()
        for item in wiki.json().get('query', {}).get('search', []):
            title = html.unescape(item.get('title', ''))
            summary = re.sub(r'<[^>]+>', '', html.unescape(item.get('snippet', '')))
            rows.append({'title': title, 'source': 'Wikipedia',
                         'url': 'https://en.wikipedia.org/wiki/' + urllib.parse.quote(title.replace(' ', '_')),
                         'summary': summary})
        news = requests.get('https://news.google.com/rss/search', timeout=8, headers=headers,
                            params={'q': phrase, 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'})
        news.raise_for_status()
        root = ET.fromstring(news.content)
        for item in root.findall('.//item')[:8]:
            title = html.unescape(item.findtext('title') or '')
            rows.append({'title': title, 'source': 'Google News',
                         'url': item.findtext('link') or '',
                         'summary': html.unescape(item.findtext('description') or '')})
        return rows

    def _finish_search(self):
        for mode, rows in self.results.items():
            tree, _details = self.views[mode]
            tree.delete(*tree.get_children())
            for index, row in enumerate(rows):
                tree.insert('', 'end', iid=str(index), values=(row['title'], row['source']))
        self.search_button.config(state='normal' if self.online else 'disabled')
        total = sum(len(rows) for rows in self.results.values())
        self.status.set(f'{total} results across {len(MODES)} Library tabs')

    def current_mode(self):
        return MODES[self.notebook.index(self.notebook.select())]

    def show_details(self, mode):
        tree, details = self.views[mode]
        selected = tree.selection()
        if not selected:
            return
        row = self.results[mode][int(selected[0])]
        text = f"{row['title']}\n\nSource: {row['source']}\n\n{re.sub(r'<[^>]+>', '', row['summary'])}\n\n{row['url']}"
        details.config(state='normal')
        details.delete('1.0', 'end')
        details.insert('1.0', text)
        details.config(state='disabled')

    def open_current(self):
        self.open_selected(self.current_mode())

    def open_selected(self, mode):
        tree, _details = self.views[mode]
        selected = tree.selection()
        if selected:
            url = self.results[mode][int(selected[0])]['url']
            if url:
                webbrowser.open_new_tab(url)

    def search_browser(self):
        if not self.online:
            self.status.set('Not Connected')
            return
        mode = self.current_mode()
        phrase = f'{self.query.get().strip() or self.category.get()} {self.category.get()} {mode}'
        url = 'https://www.google.com/search?q=' + urllib.parse.quote_plus(phrase)
        selected = self.browser.get()
        if selected == 'Google / Default':
            webbrowser.open_new_tab(url)
            return
        targets = ('Microsoft Edge', 'Firefox', 'Safari') if selected == 'All installed browsers' else (selected,)
        opened = 0
        for target in targets:
            executable = self._browser_executable(target)
            if executable:
                subprocess.Popen([executable, url])
                opened += 1
        if not opened:
            messagebox.showwarning('Browser not found',
                                   f'{selected} is not installed or could not be located.')

    @staticmethod
    def _browser_executable(name):
        candidates = {
            'Microsoft Edge': ('msedge.exe', os.path.expandvars(r'%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe'),
                               os.path.expandvars(r'%ProgramFiles%\Microsoft\Edge\Application\msedge.exe')),
            'Firefox': ('firefox.exe', os.path.expandvars(r'%ProgramFiles%\Mozilla Firefox\firefox.exe')),
            'Safari': ('safari.exe', os.path.expandvars(r'%ProgramFiles%\Safari\Safari.exe'),
                       os.path.expandvars(r'%ProgramFiles(x86)%\Safari\Safari.exe')),
        }
        for candidate in candidates.get(name, ()):
            resolved = shutil.which(candidate) or candidate
            if resolved and os.path.isfile(resolved):
                return resolved
        return None


def build_library_tool(parent):
    return LibraryTool(parent)
