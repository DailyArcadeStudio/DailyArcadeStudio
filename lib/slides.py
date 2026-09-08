"""JapanTechStudio スライドレンダラ。
1枚のスライドを PNG で描く。ダークテーマ(GitHub dark系)、コードは Pygments ハイライト。
横 1920x1080。コードは行ごとに reveal（タイピング風）できるよう n_lines を指定可能。
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pygments import lex
from pygments.lexers import PythonLexer, JavaLexer
from pygments.token import Token

LEXERS = {"python": PythonLexer(), "java": JavaLexer()}
_LANG = {"cur": "java"}  # デフォルト言語（problemのlangで上書き）

def set_lang(lang):
    _LANG["cur"] = lang if lang in LEXERS else "java"

W, H = 1920, 1080

# --- GitHub dark 系パレット ---
BG        = (13, 17, 23)      # #0d1117 背景
PANEL     = (22, 27, 34)      # #161b22 コードパネル
BORDER    = (48, 54, 61)      # #30363d 枠
FG        = (230, 237, 243)   # 本文
MUTED     = (139, 148, 158)   # 補足
ACCENT    = (88, 166, 255)    # 青(見出しアクセント)
GREEN     = (63, 185, 80)      # 最適/OK
RED       = (248, 81, 73)      # 遅い/NG
YELLOW    = (210, 168, 76)     # 強調

# Pygments トークン -> 色（VS Code darkっぽく）
TOK_COLOR = {
    Token.Keyword:               (255, 123, 114),  # if/for/return/public
    Token.Keyword.Type:          (121, 192, 255),  # Java: int, void, boolean
    Token.Keyword.Declaration:   (255, 123, 114),  # Java: class, public, static
    Token.Keyword.Constant:      (121, 192, 255),  # true/false/null
    Token.Name.Function:         (210, 168, 255),
    Token.Name.Builtin:          (121, 192, 255),
    Token.Name.Class:            (121, 214, 255),  # Java: HashMap, Map, Integer
    Token.Name.Namespace:        (121, 214, 255),
    Token.Name.Attribute:        (121, 192, 255),
    Token.Name.Decorator:        (210, 168, 255),  # @Override
    Token.Literal.String:        (165, 214, 255),
    Token.Literal.String.Doc:    (165, 214, 255),
    Token.Literal.Number:        (121, 192, 255),
    Token.Comment:               (139, 148, 158),
    Token.Operator:              (255, 123, 114),
    Token.Name:                  (230, 237, 243),
    Token.Punctuation:           (230, 237, 243),
}

FONTS = {
    "mono": "/System/Library/Fonts/Menlo.ttc",
    "sans": "/System/Library/Fonts/Helvetica.ttc",
    "sans_bold": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
}

def _font(kind, size):
    return ImageFont.truetype(FONTS[kind], size)

def tok_color(tok):
    t = tok
    while t is not None:
        if t in TOK_COLOR:
            return TOK_COLOR[t]
        t = t.parent
    return FG

def draw_kicker(d, text, x, y):
    """小さなラベル（PROBLEM / OPTIMAL 等）"""
    f = _font("sans_bold", 30)
    d.text((x, y), text.upper(), font=f, fill=ACCENT)
    w = d.textlength(text.upper(), font=f)
    d.line((x, y + 44, x + w, y + 44), fill=ACCENT, width=3)

def draw_title(d, text, x, y, size=76, color=FG):
    d.text((x, y), text, font=_font("sans_bold", size), fill=color)

def draw_bullets(d, items, x, y, size=44, gap=30, color=FG, max_w=1580):
    f = _font("sans", size)
    fb = _font("sans_bold", size)
    indent = 46
    line_h = int(size * 1.18)
    for it in items:
        # 先頭マーカー（▸ は Helvetica に無いので塗り三角で描く）
        my = y + size * 0.30
        d.polygon([(x, my), (x, my + size*0.42), (x + size*0.34, my + size*0.21)], fill=ACCENT)
        # **強調** を (word, bold) 単位に割り、幅で折り返す
        words = []
        for seg, bold in _split_bold(it):
            for w in seg.split(" "):
                if w == "":
                    continue      # a bold run ending mid-sentence leaves empty
                words.append((w, bold))   # words that would render as tofu
        cx, cy = x + indent, y
        base = cy + size          # ベースラインy（bold/regularをここで揃える）
        limit = x + max_w
        for wi, (w, bold) in enumerate(words):
            ff = fb if bold else f
            col = YELLOW if bold else color
            # no space before closing punctuation, or a bold run reads "endless ,"
            piece = w if (wi == 0 or w[0] in ",.:;!?)") else " " + w
            pw = d.textlength(piece, font=ff)
            if cx + pw > limit and cx > x + indent:
                cy += line_h
                base = cy + size
                cx = x + indent
                piece = w
                pw = d.textlength(piece, font=ff)
            d.text((cx, base), piece, font=ff, fill=col, anchor="ls")
            cx += pw
        y = cy + size + gap
    return y

def _split_bold(s):
    """**x** を (text, bold) 列に。"""
    out, i = [], 0
    while True:
        a = s.find("**", i)
        if a < 0:
            out.append((s[i:], False)); break
        out.append((s[i:a], False))
        b = s.find("**", a + 2)
        if b < 0:
            out.append((s[a:], False)); break
        out.append((s[a+2:b], True))
        i = b + 2
    return [(t, bd) for t, bd in out if t]

def _fit_code_font(d, lines, w, h, bar_h, gutter_w):
    """行数と最長行から、パネルに収まる mono フォントサイズを決める。"""
    avail_h = h - bar_h - 48
    longest = max(lines, key=len) if lines else ""
    fs = 44
    while fs >= 22:
        fm = _font("mono", fs)
        line_h = int(fs * 1.42)
        text_w = d.textlength(longest, font=fm)
        if len(lines) * line_h <= avail_h and (34 + gutter_w + text_w) <= (w - 34):
            return fs
        fs -= 2
    return 22

def draw_code_panel(d, img, code, x, y, w, h, n_lines=None, font_size=None,
                    title="solution.py", highlight_lines=None):
    """コードパネル。n_lines を渡すとその行数までしか描かない（タイピング風）。
    font_size=None なら行数と幅に合わせて自動フィット。
    highlight_lines=[3,4] のように渡すと、その行(1始まり)を黄色帯＋▶で強調。"""
    highlight_lines = set(highlight_lines or [])
    # パネル背景
    d.rounded_rectangle((x, y, x + w, y + h), radius=16, fill=PANEL, outline=BORDER, width=2)
    # タイトルバー
    bar_h = 52
    d.rounded_rectangle((x, y, x + w, y + bar_h), radius=16, fill=(30, 36, 44))
    d.rectangle((x, y + bar_h - 16, x + w, y + bar_h), fill=(30, 36, 44))
    for i, c in enumerate([(255,95,86),(255,189,46),(39,201,63)]):
        d.ellipse((x + 24 + i*30, y + 18, x + 40 + i*30, y + 34), fill=c)
    d.text((x + 140, y + 14), title, font=_font("mono", 26), fill=MUTED)

    lines = code.split("\n")
    gutter_w = 60
    if font_size is None:
        font_size = _fit_code_font(d, lines, w, h, bar_h, gutter_w)
    fm = _font("mono", font_size)
    line_h = int(font_size * 1.42)
    pad_x, pad_y = 34, bar_h + 24
    draw_lines = lines if n_lines is None else lines[:n_lines]
    for li, line in enumerate(draw_lines):
        ly = y + pad_y + li * line_h
        # 強調行: 黄色の半透明帯＋左端に▶
        if (li + 1) in highlight_lines:
            band_y0, band_y1 = ly - 4, ly + font_size + 8
            # 帯（黄色を薄く重ねる）
            band = Image.new("RGBA", (w - 24, band_y1 - band_y0), (210, 168, 76, 46))
            img.paste(band, (x + 12, band_y0), band)
            d.rounded_rectangle((x + 12, band_y0, x + w - 12, band_y1),
                                radius=8, outline=(210, 168, 76), width=2)
            # ▶ 三角マーカー
            ax = x + 16
            ay = ly + font_size * 0.15
            d.polygon([(ax, ay), (ax, ay + font_size*0.55), (ax + font_size*0.4, ay + font_size*0.28)],
                      fill=YELLOW)
        # 行番号
        d.text((x + pad_x, ly), str(li + 1).rjust(2), font=_font("mono", int(font_size*0.7)),
               fill=(80, 88, 98))
        # コード（シンタックスハイライト）
        cx = x + pad_x + gutter_w
        for tok, val in lex(line + "\n", LEXERS[_LANG["cur"]]):
            val = val.rstrip("\n")
            if not val:
                continue
            col = tok_color(tok)
            d.text((cx, ly), val, font=fm, fill=col)
            cx += d.textlength(val, font=fm)

def base_canvas():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # 下部に薄いブランドバー
    d.text((W - 420, H - 56), "Daily Arcade Studio", font=_font("sans_bold", 30), fill=(70, 78, 88))
    return img, d


def _wrap(d, text, font, max_w):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_scene(scene, n_code_lines=None):
    """1シーンを PNG(Image) にして返す。n_code_lines でコードのタイピング途中を描ける。"""
    img, d = base_canvas()
    kind = scene["kind"]
    kicker = scene.get("kicker", "")

    if kind in ("hook", "outro"):
        # 中央寄せの大タイトル
        if kicker:
            f = _font("sans_bold", 34)
            kw = d.textlength(kicker.upper(), font=f)
            d.text(((W - kw) / 2, 300), kicker.upper(), font=f, fill=ACCENT)
        tf = _font("sans_bold", 130)
        title = scene["title"]
        tw = d.textlength(title, font=tf)
        d.text(((W - tw) / 2, 370), title, font=tf, fill=FG)
        sub = scene.get("subtitle", "")
        if sub:
            sf = _font("sans", 48)
            for i, ln in enumerate(_wrap(d, sub, sf, W * 0.8)):
                lw = d.textlength(ln, font=sf)
                d.text(((W - lw) / 2, 560 + i * 66), ln, font=sf, fill=MUTED)
        return img

    # 共通ヘッダ
    if kicker:
        draw_kicker(d, kicker, 120, 90)
    draw_title(d, scene["title"], 120, 150, size=72)

    has_code = "code" in scene
    has_bullets = "bullets" in scene

    if has_code and has_bullets:
        draw_code_panel(d, img, scene["code"], 120, 310, 1080, 650,
                        n_lines=n_code_lines, title=scene.get("code_title", "solution.py"))
        draw_bullets(d, scene["bullets"], 1260, 350, size=40, gap=30, max_w=600)
    elif has_code:
        draw_code_panel(d, img, scene["code"], 120, 310, 1400, 650,
                        n_lines=n_code_lines, title=scene.get("code_title", "solution.py"))
    elif has_bullets:
        # 箇条書きが多いほど文字を少し小さく＆上詰め
        n = len(scene["bullets"])
        size = 54 if n <= 3 else (48 if n == 4 else 44)
        gap = 44 if n <= 3 else (36 if n == 4 else 30)
        draw_bullets(d, scene["bullets"], 140, 330, size=size, gap=gap, max_w=1620)
    return img
