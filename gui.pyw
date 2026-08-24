# -*- coding: utf-8 -*-
"""
괄호 → 문자 스타일  (맥 / Windows 공용)

원고를 붙여넣고 단추 하나. 괄호가 사라지고 안쪽 글자에 문자 스타일이 붙은 채로
클립보드에 담긴다. 인디자인에 그대로 붙여넣으면 된다.

실행:
    맥       ./실행-맥.command  (또는 /opt/homebrew/bin/python3 gui.pyw)
    Windows  gui.pyw 를 더블클릭
"""
import json
import os
import sys
import traceback

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine
import clipboard_rtf


APP_NAME = 'ParenStyle'
GREY = '#888'

DEFAULTS = {
    'para_style': '[기본 단락]',
    'use_para': True,
    'keep_parens': False,
    'base_style': '윗첨자',
    'kinds': {
        '한자': {'on': True,  'style': '한자윗첨자'},
        '숫자': {'on': False, 'style': ''},
        '영문': {'on': False, 'style': ''},
        '한글': {'on': False, 'style': ''},
    },
    'presets': {},
}

KIND_HINT = {
    '한자': '孔子  論語',
    '숫자': '12  ３４',
    '영문': 'Kant  abc',
    '한글': '가나다',
}


def config_path():
    if sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support')
    elif sys.platform.startswith('win'):
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    else:
        base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    d = os.path.join(base, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'settings.json')


def load_settings():
    import copy
    s = copy.deepcopy(DEFAULTS)
    try:
        with open(config_path(), encoding='utf-8') as f:
            saved = json.load(f)
    except Exception:
        return s                      # 없거나 깨졌으면 기본값으로
    if not isinstance(saved, dict):
        return s
    for k in ('para_style', 'use_para', 'keep_parens', 'base_style'):
        if k in saved:
            s[k] = saved[k]
    if isinstance(saved.get('kinds'), dict):
        for kind in engine.KINDS:
            v = saved['kinds'].get(kind)
            if isinstance(v, dict):
                s['kinds'][kind]['on'] = bool(v.get('on', False))
                s['kinds'][kind]['style'] = str(v.get('style', ''))
    if isinstance(saved.get('presets'), dict):
        s['presets'] = saved['presets']
    return s


def save_settings(s):
    try:
        with open(config_path(), 'w', encoding='utf-8') as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


class App:
    def __init__(self, root):
        self.root = root
        self.s = load_settings()

        root.title('괄호 → 문자 스타일')
        root.minsize(620, 620)

        outer = ttk.Frame(root, padding=12)
        outer.pack(fill='both', expand=True)

        # ───────────── 1. 단락 스타일 ─────────────
        b1 = ttk.LabelFrame(outer, text='1단계 · 단락 스타일 (본문 전체)', padding=10)
        b1.pack(fill='x')
        b1.columnconfigure(1, weight=1)

        self.v_use_para = tk.BooleanVar(value=self.s['use_para'])
        ttk.Checkbutton(b1, text='물린다', variable=self.v_use_para,
                        command=self.toggle_para).grid(row=0, column=0, sticky='w')
        self.v_para = tk.StringVar(value=self.s['para_style'])
        self.e_para = ttk.Entry(b1, textvariable=self.v_para)
        self.e_para.grid(row=0, column=1, sticky='ew', padx=(8, 0))
        ttk.Label(b1, text='끄면 붙여넣는 자리의 단락 스타일을 그대로 씁니다.',
                  foreground=GREY).grid(row=1, column=1, sticky='w', padx=(8, 0), pady=(3, 0))

        # ───────────── 2. 문자 스타일 ─────────────
        b2 = ttk.LabelFrame(outer, text='2단계 · 문자 스타일 (괄호 안쪽)', padding=10)
        b2.pack(fill='x', pady=(10, 0))
        b2.columnconfigure(2, weight=1)

        ttk.Label(b2, text='기본', width=6).grid(row=0, column=0, sticky='w')
        ttk.Label(b2, text='', width=10).grid(row=0, column=1)
        self.v_base = tk.StringVar(value=self.s['base_style'])
        ttk.Entry(b2, textvariable=self.v_base).grid(row=0, column=2, sticky='ew')
        ttk.Label(b2, text='아래에 안 걸린 나머지 전부', foreground=GREY)\
            .grid(row=1, column=2, sticky='w', pady=(2, 8))

        ttk.Separator(b2, orient='horizontal').grid(row=2, column=0, columnspan=3,
                                                    sticky='ew', pady=(0, 8))

        self.v_kind_on, self.v_kind_style, self.e_kind = {}, {}, {}
        r = 3
        for kind in engine.KINDS:
            conf = self.s['kinds'][kind]
            von = tk.BooleanVar(value=conf['on'])
            vst = tk.StringVar(value=conf['style'])
            self.v_kind_on[kind] = von
            self.v_kind_style[kind] = vst
            ttk.Checkbutton(b2, text=kind, variable=von, width=6,
                            command=self.on_rules_changed).grid(row=r, column=0, sticky='w')
            ttk.Label(b2, text=KIND_HINT[kind], foreground=GREY, width=10)\
                .grid(row=r, column=1, sticky='w')
            e = ttk.Entry(b2, textvariable=vst)
            e.grid(row=r, column=2, sticky='ew', pady=1)
            self.e_kind[kind] = e
            r += 1

        ttk.Label(b2, text='켠 갈래만 따로 빠지고, 나머지는 전부 기본으로 갑니다.',
                  foreground=GREY).grid(row=r, column=2, sticky='w', pady=(6, 0))

        self.v_keep = tk.BooleanVar(value=self.s['keep_parens'])
        ttk.Checkbutton(b2, text='괄호를 남긴다 (지우지 않고 서식만 입힘)',
                        variable=self.v_keep).grid(row=r + 1, column=0, columnspan=3,
                                                   sticky='w', pady=(8, 0))

        # ───────────── 저장해 둔 설정 ─────────────
        pre = ttk.Frame(outer)
        pre.pack(fill='x', pady=(10, 0))
        ttk.Label(pre, text='저장해 둔 설정').pack(side='left')
        self.v_preset = tk.StringVar()
        self.cb_preset = ttk.Combobox(pre, textvariable=self.v_preset,
                                      state='readonly', width=20)
        self.cb_preset.pack(side='left', padx=6)
        self.cb_preset.bind('<<ComboboxSelected>>', self.apply_preset)
        ttk.Button(pre, text='저장', width=6, command=self.save_preset).pack(side='left')
        ttk.Button(pre, text='삭제', width=6, command=self.delete_preset).pack(side='left', padx=(4, 0))
        self.refresh_presets()

        # ───────────── 원고 ─────────────
        b3 = ttk.LabelFrame(outer, text='원고', padding=8)
        b3.pack(fill='both', expand=True, pady=(10, 0))

        bar = ttk.Frame(b3)
        bar.pack(fill='x', pady=(0, 6))
        ttk.Button(bar, text='클립보드에서 가져오기', command=self.from_clipboard).pack(side='left')
        ttk.Button(bar, text='파일 열기…', command=self.from_file).pack(side='left', padx=(6, 0))
        ttk.Button(bar, text='비우기', command=self.clear).pack(side='left', padx=(6, 0))
        ttk.Button(bar, text='보기 예시 넣기', command=self.sample).pack(side='left', padx=(6, 0))

        wrap = ttk.Frame(b3)
        wrap.pack(fill='both', expand=True)
        self.txt = tk.Text(wrap, wrap='word', height=9, undo=True, font=self.pick_font())
        sb = ttk.Scrollbar(wrap, orient='vertical', command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        self.txt.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        self.txt.bind('<KeyRelease>', lambda e: self.on_rules_changed())

        # ───────────── 실행 ─────────────
        run = ttk.Frame(outer)
        run.pack(fill='x', pady=(10, 0))
        ttk.Button(run, text='변환해서 클립보드에 담기',
                   command=self.convert).pack(side='left')
        ttk.Button(run, text='RTF 파일로 저장…', command=self.save_rtf).pack(side='left', padx=(6, 0))

        self.v_status = tk.StringVar(value='원고를 붙여넣으세요.')
        ttk.Label(outer, textvariable=self.v_status, foreground='#2a7a4a')\
            .pack(fill='x', pady=(8, 0))

        self.toggle_para()
        self.on_rules_changed()
        root.protocol('WM_DELETE_WINDOW', self.on_close)
        root.bind('<Command-Return>', lambda e: self.convert())
        root.bind('<Control-Return>', lambda e: self.convert())
        self.txt.focus_set()

    # ───────────────────────────────────────────
    def pick_font(self):
        try:
            import tkinter.font as tkfont
            fams = set(tkfont.families())
            for name in ('Apple SD Gothic Neo', 'Malgun Gothic', 'AppleGothic', 'Noto Sans KR'):
                if name in fams:
                    return (name, 13)
        except Exception:
            pass
        return ('TkDefaultFont', 13)

    def toggle_para(self):
        self.e_para.configure(state='normal' if self.v_use_para.get() else 'disabled')

    def rules(self):
        r = {engine.FALLBACK: self.v_base.get().strip()}
        for kind in engine.KINDS:
            if self.v_kind_on[kind].get():
                name = self.v_kind_style[kind].get().strip()
                if name:
                    r[kind] = name
        return r

    def on_rules_changed(self):
        for kind in engine.KINDS:
            self.e_kind[kind].configure(
                state='normal' if self.v_kind_on[kind].get() else 'disabled')
        text = self.txt.get('1.0', 'end-1c')
        n = engine.count_parens(text)
        if not n:
            self.v_status.set('괄호가 없습니다.' if text.strip() else '원고를 붙여넣으세요.')
            return
        t = engine.tally(text, self.rules())
        detail = ', '.join('%s %d' % (k, v) for k, v in
                           sorted(t.items(), key=lambda kv: -kv[1]))
        self.v_status.set('괄호 %d곳 — %s' % (n, detail))

    def clear(self):
        self.txt.delete('1.0', 'end')
        self.on_rules_changed()

    def sample(self):
        self.txt.delete('1.0', 'end')
        self.txt.insert('1.0',
                        '공자(孔子)는 논어(論語)에서 이렇게 말했다(주석1).\n'
                        '칸트(Kant)의 정언명령과 각주(12)도 섞여 있다.\n'
                        '괄호 없는 줄은 그대로 남는다.')
        self.on_rules_changed()

    def from_clipboard(self):
        try:
            t = clipboard_rtf.get_clipboard_text()
        except Exception as e:
            messagebox.showerror('오류', str(e))
            return
        if not t.strip():
            self.v_status.set('클립보드가 비어 있습니다.')
            return
        self.txt.delete('1.0', 'end')
        self.txt.insert('1.0', t)
        self.on_rules_changed()

    def from_file(self):
        p = filedialog.askopenfilename(title='원고 열기',
                                       filetypes=[('텍스트', '*.txt'), ('모든 파일', '*.*')])
        if not p:
            return
        for enc in ('utf-8', 'cp949', 'utf-16'):
            try:
                with open(p, encoding=enc) as f:
                    t = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            messagebox.showerror('오류', '글자 인코딩을 알 수 없습니다.')
            return
        self.txt.delete('1.0', 'end')
        self.txt.insert('1.0', t)
        self.on_rules_changed()

    def gather(self):
        text = self.txt.get('1.0', 'end-1c')
        if not text.strip():
            self.v_status.set('원고가 비었습니다.')
            return None
        rules = self.rules()
        if not rules.get(engine.FALLBACK):
            messagebox.showwarning('확인', "'기본' 문자 스타일 이름을 적어 주세요.")
            return None
        for kind in engine.KINDS:
            if self.v_kind_on[kind].get() and not self.v_kind_style[kind].get().strip():
                messagebox.showwarning('확인',
                                       "'%s' 를 켜셨는데 스타일 이름이 비었습니다." % kind)
                return None
        para = self.v_para.get().strip() if self.v_use_para.get() else None
        if self.v_use_para.get() and not para:
            messagebox.showwarning('확인', '단락 스타일 이름을 적거나 체크를 끄세요.')
            return None
        rtf = engine.build_rtf(text, rules, para, self.v_keep.get())
        plain = text if self.v_keep.get() else engine.strip_parens(text)
        return text, rtf, plain

    def convert(self):
        got = self.gather()
        if not got:
            return
        text, rtf, plain = got
        try:
            clipboard_rtf.set_clipboard(rtf, plain)
        except Exception as e:
            messagebox.showerror('클립보드 오류', str(e))
            return
        t = engine.tally(text, self.rules())
        detail = ', '.join('%s %d곳' % (k, v) for k, v in
                           sorted(t.items(), key=lambda kv: -kv[1]))
        self.v_status.set('담았습니다 — %s. 인디자인에 붙여넣으세요.' % detail)

    def save_rtf(self):
        got = self.gather()
        if not got:
            return
        _, rtf, _ = got
        p = filedialog.asksaveasfilename(title='RTF 로 저장', defaultextension='.rtf',
                                         filetypes=[('서식 있는 글', '*.rtf')])
        if not p:
            return
        with open(p, 'w', encoding='ascii') as f:
            f.write(rtf)
        self.v_status.set('저장했습니다. 인디자인 파일 > 가져오기로 넣어도 됩니다.')

    # ── 저장해 둔 설정 ──
    def snapshot(self):
        return {
            'para_style': self.v_para.get(),
            'use_para': self.v_use_para.get(),
            'keep_parens': self.v_keep.get(),
            'base_style': self.v_base.get(),
            'kinds': {k: {'on': self.v_kind_on[k].get(),
                          'style': self.v_kind_style[k].get()} for k in engine.KINDS},
        }

    def restore(self, p):
        self.v_para.set(p.get('para_style', ''))
        self.v_use_para.set(bool(p.get('use_para', True)))
        self.v_keep.set(bool(p.get('keep_parens', False)))
        self.v_base.set(p.get('base_style', ''))
        for k in engine.KINDS:
            c = (p.get('kinds') or {}).get(k) or {}
            self.v_kind_on[k].set(bool(c.get('on', False)))
            self.v_kind_style[k].set(c.get('style', ''))
        self.toggle_para()
        self.on_rules_changed()

    def refresh_presets(self):
        names = sorted(self.s['presets'].keys())
        self.cb_preset['values'] = names
        if not names:
            self.v_preset.set('')

    def apply_preset(self, _evt=None):
        p = self.s['presets'].get(self.v_preset.get())
        if p:
            self.restore(p)
            self.v_status.set("'%s' 설정을 불러왔습니다." % self.v_preset.get())

    def save_preset(self):
        name = SimpleAsk(self.root, '설정 이름', '어떤 이름으로 저장할까요?',
                         self.v_preset.get()).result
        if not name:
            return
        self.s['presets'][name] = self.snapshot()
        save_settings(dict(self.s, **self.snapshot()))
        self.refresh_presets()
        self.v_preset.set(name)
        self.v_status.set("'%s' 로 저장했습니다." % name)

    def delete_preset(self):
        name = self.v_preset.get()
        if not name or name not in self.s['presets']:
            return
        if not messagebox.askyesno('삭제', "'%s' 를 지울까요?" % name):
            return
        del self.s['presets'][name]
        save_settings(dict(self.s, **self.snapshot()))
        self.refresh_presets()
        self.v_status.set('지웠습니다.')

    def on_close(self):
        s = dict(self.s)
        s.update(self.snapshot())
        save_settings(s)
        self.root.destroy()


class SimpleAsk(tk.Toplevel):
    """한 줄 물어보는 작은 창."""
    def __init__(self, parent, title, prompt, initial=''):
        super().__init__(parent)
        self.result = None
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)
        f = ttk.Frame(self, padding=14)
        f.pack(fill='both', expand=True)
        ttk.Label(f, text=prompt).pack(anchor='w')
        v = tk.StringVar(value=initial)
        e = ttk.Entry(f, textvariable=v, width=30)
        e.pack(fill='x', pady=8)
        e.focus_set()
        e.select_range(0, 'end')

        def ok(_=None):
            self.result = v.get().strip() or None
            self.destroy()

        row = ttk.Frame(f)
        row.pack(fill='x')
        ttk.Button(row, text='확인', command=ok).pack(side='right')
        ttk.Button(row, text='취소', command=self.destroy).pack(side='right', padx=(0, 6))
        e.bind('<Return>', ok)
        self.bind('<Escape>', lambda _e: self.destroy())
        self.grab_set()
        parent.wait_window(self)


def check_tk(root):
    """맥 시스템 파이썬의 Tk 8.5 는 창을 빈 화면으로 그린다. 미리 잡아준다."""
    try:
        ver = root.tk.call('info', 'patchlevel')
        major, minor = (int(x) for x in ver.split('.')[:2])
    except Exception:
        return
    if (major, minor) < (8, 6):
        messagebox.showerror(
            '오래된 Tk',
            'Tk %s 로 돌고 있습니다. 이 판은 창을 빈 화면으로 그립니다.\n\n'
            '맥: /opt/homebrew/bin/python3 gui.pyw 로 실행하거나\n'
            '     실행-맥.command 를 쓰세요.\n'
            'Windows: python.org 판 파이썬을 쓰세요.' % ver)


def main():
    root = tk.Tk()
    check_tk(root)
    try:
        App(root)
    except Exception:
        messagebox.showerror('시작 실패', traceback.format_exc())
        return
    root.mainloop()


if __name__ == '__main__':
    main()
