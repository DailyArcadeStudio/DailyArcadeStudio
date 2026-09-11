"""ゲーム画面に「?」ボタンとルール表示を足す。

ルール文は scenes.json の showcase シーン（title + bullets）から作る。
動画で説明している内容とサイトの説明が必ず一致する。

録画では邪魔なので、?auto=1 / ?showcase= / ?nochrome=1 のときは
「?」も「‹ All games」も出さない。撮影後に手で足す運用にすると、
公開中のゲームを後から書き換えることになって事故りやすいので、
URLで隠す方式にしている。

usage: python lib/add_help.py <slug>
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "/Users/fukushimatakumi/develop")
from jp_ui import T as _T  # 固定文言の日英切り替え

ROOT = Path(__file__).resolve().parent.parent

CSS = """
  /* --- help (?) --- */
  #helpBtn{position:fixed;top:14px;right:66px;z-index:30;border:none;cursor:pointer;
    background:rgba(12,16,26,.72);color:#fff;font:700 20px/1 'Helvetica Neue',Arial,sans-serif;
    width:44px;height:44px;border-radius:12px;}
  #helpBtn:hover{background:rgba(30,38,56,.9);}
  #help{position:fixed;inset:0;z-index:40;display:none;align-items:center;
    justify-content:center;background:rgba(4,6,12,.82);padding:20px;}
  #help.on{display:flex;}
  #help .box{background:#111726;border:1px solid #2b3550;border-radius:18px;
    max-width:560px;width:100%;max-height:86vh;overflow:auto;padding:26px 28px 22px;
    color:#e6edf3;font-family:'Helvetica Neue',Arial,sans-serif;}
  #help h2{margin:0 0 4px;font-size:26px;}
  #help .sub{color:#8b949e;font-size:14px;margin:0 0 18px;}
  #help h3{font-size:15px;color:#ffd23b;margin:18px 0 6px;letter-spacing:.04em;}
  #help ul{margin:0;padding-left:20px;}
  #help li{font-size:15px;line-height:1.65;margin:3px 0;}
  #help b{color:#ffd23b;font-weight:700;}
  #help .close{margin-top:20px;width:100%;padding:12px;border:none;border-radius:10px;
    background:#2b3550;color:#fff;font-size:16px;font-weight:700;cursor:pointer;}
  #help .close:hover{background:#3a4668;}
"""

JS = """
// --- help (?) : ルールを見せる。録画中は出さない ---
(function(){
  const btn = document.getElementById('helpBtn');
  const panel = document.getElementById('help');
  if(!btn || !panel) return;
  if(NOCHROME){                      // 録画・showcase では画面から消す
    btn.style.display = 'none';
    const back = document.getElementById('back');
    if(back) back.style.display = 'none';
    return;
  }
  const open = () => { panel.classList.add('on'); };
  const close = () => { panel.classList.remove('on'); };
  btn.addEventListener('click', open);
  btn.addEventListener('touchend', e => { e.preventDefault(); open(); }, {passive:false});
  panel.addEventListener('click', e => { if(e.target === panel) close(); });
  panel.querySelector('.close').addEventListener('click', close);
  panel.querySelector('.close').addEventListener('touchend',
    e => { e.preventDefault(); close(); }, {passive:false});
  addEventListener('keydown', e => {
    if(e.code === 'Escape') close();
    else if(e.key === '?' || (e.code === 'Slash' && e.shiftKey)) open();
  });
})();
"""


def bullets_html(scenes):
    """showcase シーンから遊び方の項目を作る。"""
    out = []
    for sc in scenes:
        if sc.get("kind") != "showcase":
            continue
        title = sc.get("title", "").strip()
        items = sc.get("bullets") or []
        if not title or not items:
            continue
        lis = "".join(
            "<li>" + re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", b) + "</li>"
            for b in items)
        out.append(f"    <h3>{title}</h3>\n    <ul>{lis}</ul>")
    return "\n".join(out)


def main(slug):
    gdir = ROOT / "games" / slug
    html_path = gdir / "index.html"
    html = html_path.read_text()
    if 'id="helpBtn"' in html:
        print(f"SKIP {slug} (already has help)")
        return

    data = json.loads((gdir / "scenes.json").read_text())
    title = data.get("title", slug)
    hook = ((data.get("thumb") or {}).get("sub", "")
            or _T("Play it free in your browser."))
    body = bullets_html(data["scenes"])

    _howto = _T("how to play")
    panel = (f'<button id="helpBtn" title="{_howto}">?</button>\n'
             f'<div id="help"><div class="box">\n'
             f'  <h2>{title}</h2>\n'
             f'  <p class="sub">{hook}</p>\n'
             f'{body}\n'
             f'  <button class="close">{_T("Got it")}</button>\n'
             f'</div></div>')

    # ボタンとパネルは #back の隣に置く
    html = html.replace('<a id="back"', panel + '\n<a id="back"', 1)
    html = html.replace('</style>', CSS + '</style>', 1)

    # 録画では chrome を出さない。既存のフラグ群の直後に足す。
    anchor = "const SILENT ="
    i = html.index(anchor)
    line_end = html.index("\n", i) + 1
    html = (html[:line_end]
            + "// 録画・showcase では「?」と「All games」を出さない（動画の邪魔になる）\n"
              "const NOCHROME = AUTO || !!SHOWCASE_Q || QS.get('nochrome')==='1';\n"
            + html[line_end:])
    html = html.replace("</script>\n</body>", JS + "</script>\n</body>", 1)
    html_path.write_text(html)
    print(f"HELP_ADDED {slug}")


if __name__ == "__main__":
    main(sys.argv[1])
