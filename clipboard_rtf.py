# -*- coding: utf-8 -*-
"""
서식 있는 글(RTF)을 클립보드에 얹는다. 맥과 Windows 둘 다.

RTF 서랍과 평문 서랍을 함께 얹는다.
받는 쪽이 서식을 못 읽거나 안 읽기로 되어 있으면 평문 서랍을 연다.
"""
import os
import subprocess
import sys
import tempfile

IS_MAC = sys.platform == 'darwin'
IS_WIN = sys.platform.startswith('win')


# ───────────────────────── 맥 ─────────────────────────
# NSPasteboard 에 옛 방식(declareTypes:owner:)으로 얹는다. 호환이 가장 넓다.
_MAC_JXA = r'''
ObjC.import('AppKit');
function run(argv) {
  var rtfPath = argv[0], txtPath = argv[1];
  var pb = $.NSPasteboard.generalPasteboard;
  var types = $.NSArray.arrayWithArray([
      'public.rtf', 'NeXT Rich Text Format v1.0 pasteboard type',
      'public.utf8-plain-text', 'NSStringPboardType']);
  pb.declareTypesOwner(types, $());
  var rtf = $.NSData.dataWithContentsOfFile(rtfPath);
  var txt = $.NSString.stringWithContentsOfFileEncodingError(
      txtPath, $.NSUTF8StringEncoding, null);
  pb.setDataForType(rtf, 'public.rtf');
  pb.setDataForType(rtf, 'NeXT Rich Text Format v1.0 pasteboard type');
  pb.setStringForType(txt, 'public.utf8-plain-text');
  pb.setStringForType(txt, 'NSStringPboardType');
  return 'ok';
}
'''


def _set_mac(rtf, plain):
    d = tempfile.mkdtemp(prefix='parenstyle-')
    rp = os.path.join(d, 'out.rtf')
    tp = os.path.join(d, 'out.txt')
    jp = os.path.join(d, 'w.js')
    # RTF 본문은 순수 아스키다 (한글은 \uN 으로 escape 되어 있다)
    with open(rp, 'w', encoding='ascii') as f:
        f.write(rtf)
    with open(tp, 'w', encoding='utf-8') as f:
        f.write(plain)
    with open(jp, 'w', encoding='utf-8') as f:
        f.write(_MAC_JXA)
    r = subprocess.run(['osascript', '-l', 'JavaScript', jp, rp, tp],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('클립보드에 얹지 못했습니다:\n' + (r.stderr or '').strip())


# ─────────────────────── Windows ───────────────────────
def _set_win(rtf, plain):
    import ctypes
    from ctypes import wintypes

    u32 = ctypes.WinDLL('user32', use_last_error=True)
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)

    u32.OpenClipboard.argtypes = [wintypes.HWND]
    u32.OpenClipboard.restype = wintypes.BOOL
    u32.EmptyClipboard.restype = wintypes.BOOL
    u32.CloseClipboard.restype = wintypes.BOOL
    u32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    u32.SetClipboardData.restype = wintypes.HANDLE
    u32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
    u32.RegisterClipboardFormatW.restype = wintypes.UINT

    k32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    k32.GlobalAlloc.restype = wintypes.HGLOBAL
    k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    k32.GlobalLock.restype = wintypes.LPVOID
    k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    k32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    k32.GlobalFree.restype = wintypes.HGLOBAL

    GMEM_MOVEABLE = 0x0002
    CF_UNICODETEXT = 13
    CF_RTF = u32.RegisterClipboardFormatW('Rich Text Format')
    if not CF_RTF:
        raise RuntimeError('RTF 클립보드 형식을 등록하지 못했습니다.')

    # 윈도우 줄바꿈으로 맞춘다
    plain_win = plain.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')

    payloads = [
        # RTF 는 순수 아스키. 끝에 NUL 을 붙인다.
        (CF_RTF, rtf.encode('ascii') + b'\x00'),
        (CF_UNICODETEXT, plain_win.encode('utf-16-le') + b'\x00\x00'),
    ]

    if not u32.OpenClipboard(None):
        raise RuntimeError('클립보드를 열지 못했습니다. 다른 프로그램이 쥐고 있을 수 있습니다.')
    try:
        u32.EmptyClipboard()
        for fmt, data in payloads:
            h = k32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not h:
                raise RuntimeError('메모리를 잡지 못했습니다.')
            p = k32.GlobalLock(h)
            if not p:
                k32.GlobalFree(h)
                raise RuntimeError('메모리를 잠그지 못했습니다.')
            ctypes.memmove(p, data, len(data))
            k32.GlobalUnlock(h)
            if not u32.SetClipboardData(fmt, h):
                k32.GlobalFree(h)
                raise RuntimeError('클립보드에 넣지 못했습니다.')
            # 성공하면 소유권이 시스템으로 넘어간다. 여기서 풀면 안 된다.
    finally:
        u32.CloseClipboard()


# ─────────────────────── 공통 ───────────────────────
def set_clipboard(rtf, plain):
    if IS_MAC:
        _set_mac(rtf, plain)
    elif IS_WIN:
        _set_win(rtf, plain)
    else:
        raise RuntimeError('맥과 Windows 만 지원합니다. (지금: %s)' % sys.platform)


def get_clipboard_rtf():
    """클립보드의 RTF 서랍을 읽는다. 없으면 ''. (자가진단용)"""
    if IS_MAC:
        # pbpaste -Prefer rtf 는 평문을 돌려준다. NSPasteboard 에서 직접 읽어야 한다.
        jxa = ("ObjC.import('AppKit');"
               "function run(){var pb=$.NSPasteboard.generalPasteboard;"
               "var d=pb.dataForType('public.rtf');"
               "if(d.isNil())return '';"
               "var s=$.NSString.alloc.initWithDataEncoding(d,$.NSASCIIStringEncoding);"
               "return s.isNil()?'':ObjC.unwrap(s);}")
        r = subprocess.run(['osascript', '-l', 'JavaScript', '-e', jxa],
                           capture_output=True, text=True)
        out = r.stdout
        return out if out.lstrip().startswith('{\\rtf') else ''
    if IS_WIN:
        import ctypes
        from ctypes import wintypes
        u32 = ctypes.WinDLL('user32', use_last_error=True)
        k32 = ctypes.WinDLL('kernel32', use_last_error=True)
        u32.GetClipboardData.argtypes = [wintypes.UINT]
        u32.GetClipboardData.restype = wintypes.HANDLE
        u32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
        u32.RegisterClipboardFormatW.restype = wintypes.UINT
        k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        k32.GlobalLock.restype = wintypes.LPVOID
        k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        k32.GlobalSize.argtypes = [wintypes.HGLOBAL]
        k32.GlobalSize.restype = ctypes.c_size_t
        fmt = u32.RegisterClipboardFormatW('Rich Text Format')
        if not u32.OpenClipboard(None):
            return ''
        try:
            h = u32.GetClipboardData(fmt)
            if not h:
                return ''
            p = k32.GlobalLock(h)
            if not p:
                return ''
            try:
                n = k32.GlobalSize(h)
                raw = ctypes.string_at(p, n)
                return raw.split(b'\x00', 1)[0].decode('ascii', 'replace')
            finally:
                k32.GlobalUnlock(h)
        finally:
            u32.CloseClipboard()
    return ''


def get_clipboard_text():
    """클립보드의 평문을 읽는다."""
    if IS_MAC:
        r = subprocess.run(['pbpaste'], capture_output=True, text=True)
        return r.stdout
    if IS_WIN:
        import ctypes
        from ctypes import wintypes
        u32 = ctypes.WinDLL('user32', use_last_error=True)
        k32 = ctypes.WinDLL('kernel32', use_last_error=True)
        u32.GetClipboardData.argtypes = [wintypes.UINT]
        u32.GetClipboardData.restype = wintypes.HANDLE
        k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        k32.GlobalLock.restype = wintypes.LPVOID
        k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        CF_UNICODETEXT = 13
        if not u32.OpenClipboard(None):
            return ''
        try:
            h = u32.GetClipboardData(CF_UNICODETEXT)
            if not h:
                return ''
            p = k32.GlobalLock(h)
            if not p:
                return ''
            try:
                return ctypes.c_wchar_p(p).value or ''
            finally:
                k32.GlobalUnlock(h)
        finally:
            u32.CloseClipboard()
    return ''
