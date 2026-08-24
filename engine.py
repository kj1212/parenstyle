# -*- coding: utf-8 -*-
"""
원고에서 (괄호) 를 벗기고, 안쪽 글자에 문자 스타일을 물린 RTF 를 만든다.
본문 단락에는 단락 스타일을 물린다. 인디자인이 쓰는 2단계 그대로.

괄호 안 내용이 무엇이냐에 따라 서로 다른 문자 스타일을 줄 수 있다.
    한자   (孔子)   → 한자용 스타일
    숫자   (12)     → 각주번호용 스타일
    영문   (Kant)   → 영문용 스타일
    나머지          → 기본 스타일

RTF 머리말은 인디자인 자신이 뱉는 것을 본떴다.
"""
import re

PARA_STYLE_ID = 0

# 반각 ( ) 와 전각 （ ） 를 모두 잡는다. 중첩은 다루지 않는다.
PAREN = re.compile(r'[(（]([^()（）]+)[)）]')

# 갈래 이름. 위에서부터 먼저 맞는 것 하나가 적용된다. '나머지'는 언제나 마지막.
KINDS = ('한자', '숫자', '영문', '한글')
FALLBACK = '나머지'


def _is_hanja(c):
    o = ord(c)
    return (0x4E00 <= o <= 0x9FFF or      # 기본 한자
            0x3400 <= o <= 0x4DBF or      # 확장 A
            0xF900 <= o <= 0xFAFF or      # 호환 한자
            0x20000 <= o <= 0x2FA1F)      # 확장 B 이상


def _is_digit(c):
    return c.isdigit() or '０' <= c <= '９'


def _is_latin(c):
    o = ord(c)
    return (0x41 <= o <= 0x5A or 0x61 <= o <= 0x7A or
            0xFF21 <= o <= 0xFF3A or 0xFF41 <= o <= 0xFF5A)


def _is_hangul(c):
    o = ord(c)
    return 0xAC00 <= o <= 0xD7A3 or 0x1100 <= o <= 0x11FF or 0x3130 <= o <= 0x318F


# 갈래를 가릴 때 무시하는 글자 — 붙임표, 가운뎃점, 마침표, 쉼표 따위
_IGNORE = set(' 　.,·・-–—~ᆞ')


def classify(inner):
    """괄호 안 내용이 어느 갈래인지 가린다."""
    core = [c for c in inner if c not in _IGNORE]
    if not core:
        return FALLBACK
    if all(_is_hanja(c) for c in core):
        return '한자'
    if all(_is_digit(c) for c in core):
        return '숫자'
    if all(_is_latin(c) for c in core):
        return '영문'
    if all(_is_hangul(c) for c in core):
        return '한글'
    return FALLBACK


def rtf_escape(s):
    """RTF escape. 아스키 밖 글자는 \\uN ? 로 바꾼다 (결과는 순수 아스키)."""
    out = []
    for ch in s:
        o = ord(ch)
        if ch in '\\{}':
            out.append('\\' + ch)
        elif ch == '\t':
            out.append('\\tab ')
        elif o < 128:
            out.append(ch)
        elif o <= 0xFFFF:
            out.append('\\u%d ?' % (o - 65536 if o > 32767 else o))
        else:
            o -= 0x10000
            hi, lo = 0xD800 + (o >> 10), 0xDC00 + (o & 0x3FF)
            out.append('\\u%d ?\\u%d ?' % (hi - 65536, lo - 65536))
    return ''.join(out)


def strip_parens(text):
    """괄호만 벗긴 평문. 서식을 못 읽는 곳을 위한 대비책."""
    return PAREN.sub(lambda m: m.group(1), text)


def count_parens(text):
    return len(PAREN.findall(text))


def tally(text, rules):
    """갈래별로 몇 곳인지 세어 돌려준다. 창에 보여주려고."""
    out = {}
    for m in PAREN.finditer(text):
        k = pick_kind(m.group(1), rules)
        out[k] = out.get(k, 0) + 1
    return out


def pick_kind(inner, rules):
    """rules 에 실제로 켜져 있는 갈래만 따진다."""
    k = classify(inner)
    return k if k in rules else FALLBACK


def build_rtf(text, rules, para_style_name=None, keep_parens=False):
    """
    text        원고 (여러 줄 가능, 한 줄이 한 단락)
    rules       {'나머지': '윗첨자', '한자': '한자윗첨자', ...}
                '나머지' 는 반드시 있어야 한다.
    para_style_name  본문에 물릴 단락 스타일 이름. None 이면 단락 스타일을 안 건드린다
    keep_parens  True 면 괄호를 남기고 서식만 입힌다
    """
    if FALLBACK not in rules or not rules[FALLBACK]:
        raise ValueError("'나머지' 문자 스타일이 정해지지 않았습니다.")

    # 같은 스타일 이름은 같은 \csN 을 쓴다
    ids = {}
    for kind in list(KINDS) + [FALLBACK]:
        name = rules.get(kind)
        if name and name not in ids:
            ids[name] = len(ids) + 1

    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        lines = ['']

    body = []
    for line in lines:
        chunks, pos = [], 0
        for m in PAREN.finditer(line):
            if m.start() > pos:
                chunks.append(rtf_escape(line[pos:m.start()]))
            kind = pick_kind(m.group(1), rules)
            cs_id = ids[rules[kind]]
            inner = m.group(0) if keep_parens else m.group(1)
            # 본문 참조는 \* 없이 쓴다. \* 를 붙이면 "모르는 목적지"로 보고
            # 그 덩어리를 통째로 버리는 읽개가 있다.
            # \super 는 스타일 이름 매칭이 실패했을 때의 보험.
            chunks.append('{\\cs%d\\super %s}' % (cs_id, rtf_escape(inner)))
            pos = m.end()
        if pos < len(line):
            chunks.append(rtf_escape(line[pos:]))
        body.append(''.join(chunks))

    ps_name = rtf_escape(para_style_name) if para_style_name else None
    para_tag = ('\\s%d ' % PARA_STYLE_ID) if ps_name else ''

    styles = []
    if ps_name:
        styles.append(r'{\s%d\snext%d %s;}' % (PARA_STYLE_ID, PARA_STYLE_ID, ps_name))
    for name, cs_id in sorted(ids.items(), key=lambda kv: kv[1]):
        styles.append(r'{\*\cs%d \additive \super %s;}' % (cs_id, rtf_escape(name)))

    parts = [
        r'{\rtf1\mac\ansicpg949\deff0\deftab720',
        r'{\fonttbl{\f0\fnil\ftnil\cpg10003\fcharset79 AdobeMyungjoStd-Medium;}}',
        r'{\colortbl\red0\blue0\green0;}',
        r'{\stylesheet' + ''.join(styles) + '}',
        r'\ksulang1041',
    ]
    for p in body:
        parts.append(r'\pard\plain ' + para_tag + p + r'\par')
    parts.append('}')
    return '\n'.join(parts)
