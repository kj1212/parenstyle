# -*- coding: utf-8 -*-
"""
옮겨온 곳에서 제대로 도는지 스스로 검사한다.

    python 자가진단.py          (Windows)
    python3 자가진단.py         (맥)

클립보드를 덮어쓰니, 붙여넣을 게 남아 있으면 먼저 처리하고 돌릴 것.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ok_count = 0
fail_count = 0


def check(name, cond, detail=''):
    global ok_count, fail_count
    if cond:
        ok_count += 1
        print('  [통과] %s' % name)
    else:
        fail_count += 1
        print('  [실패] %s' % name)
        if detail:
            print('         %s' % detail)


print('=' * 60)
print(' 괄호 → 문자 스타일  자가진단')
print('=' * 60)
print(' 파이썬 : %s' % sys.version.split()[0])
print(' 플랫폼 : %s' % sys.platform)

# ── 1. tkinter ──────────────────────────────────────────
print('\n[1] 창 그리개 (tkinter)')
try:
    import tkinter
    tkver = str(tkinter.TkVersion)
    print('  Tk %s' % tkver)
    check('Tk 8.6 이상', float(tkver) >= 8.6,
          '맥 기본 파이썬(Tk 8.5)은 창을 빈 화면으로 그린다. '
          '실행-맥.command 를 쓰거나 brew install python-tk')
except Exception as e:
    check('tkinter 있음', False, str(e))

# ── 2. 갈래 가르기 ──────────────────────────────────────
print('\n[2] 갈래 가르기')
try:
    import engine
    cases = [('孔子', '한자'), ('論語 卷一', '한자'), ('12', '숫자'),
             ('１２', '숫자'), ('Kant', '영문'), ('가나다', '한글'),
             ('주석1', '나머지'), ('漢字a', '나머지')]
    bad = [(s, want, engine.classify(s)) for s, want in cases
           if engine.classify(s) != want]
    check('8가지 보기 모두 맞음', not bad,
          '틀린 것: %s' % bad if bad else '')
except Exception as e:
    check('engine 불러오기', False, str(e))

# ── 3. RTF 짓기 ────────────────────────────────────────
print('\n[3] RTF 짓기')
TEXT = ('공자(孔子)는 논어(論語)에서 말했다(주석1).\n'
        '칸트(Kant)와 각주(12)도 있다.\n'
        '괄호 없는 줄.')
RULES = {'나머지': '윗첨자', '한자': '한자윗첨자'}
BODY = '본문명조'
rtf = None
try:
    rtf = engine.build_rtf(TEXT, RULES, '[기본 단락]', body_char_style=BODY)
    body_part = rtf.split('\\ksulang')[-1]
    check('괄호 5곳을 찾음', engine.count_parens(TEXT) == 5,
          '찾은 수: %d' % engine.count_parens(TEXT))
    try:
        rtf.encode('ascii')
        check('결과가 순수 아스키', True)
    except UnicodeEncodeError as e:
        check('결과가 순수 아스키', False, str(e))
    check('머리말이 맞음', rtf.startswith('{\\rtf1'))
    # 본문명조 + 한자윗첨자 + 윗첨자 = 3개
    check('문자 스타일 이름 3개가 들어감', rtf.count('\\additive') == 3,
          '들어간 수: %d' % rtf.count('\\additive'))
    check("본문에 '\\*\\cs' 가 없음 (있으면 글자가 사라진다)",
          '{\\*\\cs' not in body_part)
    check('본문 글자가 문자 스타일로 감싸짐 ({\\cs1 …})', '{\\cs1 ' in body_part)
    check('위첨자 런에 \\super 가 붙음', '\\super' in body_part)
    # 예외(skip_starts): 지정한 괄호는 변환하지 않고 그대로 둔다
    check('예외 괄호는 그대로 남음',
          engine.strip_parens('가(A)나(B)', skip_starts={1}) == '가(A)나B',
          '결과: %r' % engine.strip_parens('가(A)나(B)', skip_starts={1}))
    # 병기(한글 뒤 한자): 浚(준 뒤)은 잡고, 法(공백 뒤)은 제외
    tg = engine.targets('준浚이 法은', RULES, hanja_annot=True)
    check('병기 한자 감지 (浚 잡고 공백 뒤 法 제외)',
          [s for a, b, i, w, s in tg] == ['hanja'] and tg[0][2] == '浚',
          '감지: %r' % tg)
except Exception as e:
    check('build_rtf', False, repr(e))

# ── 4. 클립보드 ────────────────────────────────────────
print('\n[4] 클립보드 (여기가 Windows 미검증 구간)')
if rtf:
    try:
        import clipboard_rtf
        plain = engine.strip_parens(TEXT)
        clipboard_rtf.set_clipboard(rtf, plain)
        check('얹기 성공', True)

        back_txt = clipboard_rtf.get_clipboard_text()
        check('평문 서랍 되읽기',
              back_txt.replace('\r\n', '\n').strip() == plain.strip(),
              '읽은 것: %r' % back_txt[:60])

        back_rtf = clipboard_rtf.get_clipboard_rtf()
        check('RTF 서랍 되읽기', back_rtf.startswith('{\\rtf1'),
              '읽은 것: %r' % back_rtf[:60])
        if back_rtf.startswith('{\\rtf1'):
            check('RTF 내용이 온전함',
                  back_rtf.count('\\additive') == 3,
                  '\\additive 수: %d' % back_rtf.count('\\additive'))
    except Exception as e:
        import traceback
        check('클립보드', False, traceback.format_exc())

# ── 5. 설정 저장 자리 ──────────────────────────────────
print('\n[5] 설정 저장 자리')
try:
    if sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support')
    elif sys.platform.startswith('win'):
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    else:
        base = os.path.expanduser('~/.config')
    d = os.path.join(base, 'ParenStyle')
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, '_write_test')
    with open(p, 'w') as f:
        f.write('x')
    os.remove(p)
    check('쓸 수 있음', True)
    print('  자리: %s' % d)
except Exception as e:
    check('쓸 수 있음', False, str(e))

# ── 마무리 ────────────────────────────────────────────
print('\n' + '=' * 60)
print(' 통과 %d / 실패 %d' % (ok_count, fail_count))
if fail_count == 0:
    print(' 다 좋습니다. 이제 인디자인 설정만 확인하세요:')
    print('   설정 > 클립보드 처리 > "모든 정보"')
    print(' 그리고 인디자인에 그냥 붙여넣어 보세요 (클립보드에 담겨 있습니다).')
else:
    print(' 실패한 항목을 문법.md 에서 찾아보세요.')
print('=' * 60)
