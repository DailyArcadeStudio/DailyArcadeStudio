"""動画の内容の確認問題ページを1枚のHTMLで作る。

動画で解説したことを理解できたか試す5問。2択。画像なし。
問題文にコード片を入れられる（等幅で表示する）。

LeetCode のような「問題を解く場」にはしない。あくまで動画の復習。

    python make_check.py <check.json> <out_dir>
"""
import json
import sys
from pathlib import Path

HTML = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<meta property="og:title" content="{title}">
<style>
  *{{box-sizing:border-box;-webkit-tap-highlight-color:transparent}}
  body{{margin:0;background:#0d1117;color:#e6edf3;
       font-family:-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;
       line-height:1.7;padding:env(safe-area-inset-top) 0 env(safe-area-inset-bottom)}}
  .wrap{{max-width:620px;margin:0 auto;padding:22px 18px 60px}}
  h1{{font-size:clamp(20px,5.4vw,27px);margin:6px 0 6px;line-height:1.4}}
  .lead{{color:#8b949e;font-size:14.5px;margin:0 0 22px}}
  .q{{background:#161b22;border:1px solid #21262d;border-radius:13px;
      padding:18px 16px;margin:0 0 14px}}
  .qn{{color:#58a6ff;font-size:12.5px;letter-spacing:.1em;margin:0 0 8px}}
  .qt{{font-size:16px;font-weight:700;margin:0 0 12px;line-height:1.65}}
  pre{{background:#0d1117;border:1px solid #21262d;border-radius:9px;
       padding:13px 14px;overflow-x:auto;margin:0 0 14px;
       font-family:"SF Mono",Menlo,monospace;font-size:13px;line-height:1.65;
       color:#c9d1d9}}
  .opts{{display:grid;gap:9px}}
  .opt{{border:1px solid #30363d;background:#0d1117;color:#e6edf3;border-radius:10px;
        padding:14px;font-size:15px;cursor:pointer;text-align:left;
        font-family:inherit;line-height:1.6;transition:.15s}}
  .opt:hover:not(:disabled){{border-color:#58a6ff}}
  .opt:disabled{{cursor:default;opacity:.75}}
  .opt.ok{{border-color:#3fb950;background:#122117;color:#7ee787;font-weight:700}}
  .opt.ng{{border-color:#f85149;background:#21121380;color:#ff9492}}
  .exp{{margin:13px 0 0;padding:13px 14px;background:#0d1117;border-left:3px solid #58a6ff;
        border-radius:0 9px 9px 0;font-size:14.5px;color:#c9d1d9;display:none}}
  .exp.on{{display:block}}
  .score{{display:none;background:#161b22;border:1px solid #21262d;border-radius:14px;
          padding:24px 20px;text-align:center;margin:18px 0 0}}
  .score.on{{display:block}}
  .snum{{font-size:44px;font-weight:800;color:#ffd23b;line-height:1.1}}
  .smsg{{font-size:16px;margin:10px 0 0}}
  .share{{display:grid;gap:10px;margin:20px 0 0}}
  .share a,.share button{{display:block;text-align:center;padding:14px;border-radius:12px;
        text-decoration:none;font-weight:700;font-size:15px;border:1px solid #30363d;
        background:#0d1117;color:#e6edf3;cursor:pointer;font-family:inherit}}
  .back{{display:inline-block;margin-top:14px;color:#8b949e;font-size:14px}}
  footer{{margin-top:30px;color:#6e7681;font-size:12.5px;text-align:center}}
</style>
</head>
<body>
<div class="wrap">
  <h1>{title}</h1>
  <p class="lead">{lead}</p>
  <div id="qs"></div>
  <div class="score" id="score">
    <div class="snum"><span id="sn">0</span> / {n}</div>
    <p class="smsg" id="sm"></p>
    <div class="share">
      <a id="tw" target="_blank" rel="noopener">結果をXに投稿する</a>
      <button id="again">もう一度</button>
    </div>
  </div>
  <a class="back" href="../">ほかの確認問題を見る</a>
  <footer>{brand}</footer>
</div>
<script>
const DATA = {data};
let done = 0, ok = 0;
const qsEl = document.getElementById('qs');

DATA.questions.forEach((q, i) => {{
  const d = document.createElement('div');
  d.className = 'q';
  let h = `<p class="qn">Q${{i+1}}</p><p class="qt">${{q.text}}</p>`;
  if (q.code) h += `<pre>${{q.code.replace(/[&<>]/g, c =>
      ({{'&':'&amp;','<':'&lt;','>':'&gt;'}})[c])}}</pre>`;
  d.innerHTML = h;
  const box = document.createElement('div');
  box.className = 'opts';
  const exp = document.createElement('div');
  exp.className = 'exp';
  exp.textContent = q.explain;
  q.options.forEach((o, k) => {{
    const b = document.createElement('button');
    b.className = 'opt';
    b.textContent = o;
    b.onclick = () => {{
      [...box.children].forEach(c => c.disabled = true);
      const hit = (k === q.answer);
      b.classList.add(hit ? 'ok' : 'ng');
      if (!hit) box.children[q.answer].classList.add('ok');
      exp.classList.add('on');
      done++; if (hit) ok++;
      if (done === DATA.questions.length) finish();
    }};
    box.appendChild(b);
  }});
  d.appendChild(box); d.appendChild(exp);
  qsEl.appendChild(d);
}});

function finish() {{
  const n = DATA.questions.length;
  document.getElementById('sn').textContent = ok;
  const msgs = DATA.messages || {{}};
  document.getElementById('sm').textContent =
    ok === n ? (msgs.perfect || '全問正解です。') :
    ok >= n * 0.6 ? (msgs.good || 'だいたい掴めています。') :
    (msgs.retry || 'もう一度動画を見てみてください。');
  const txt = encodeURIComponent(`${{DATA.title}}\\n${{ok}}/${{n}} 正解でした。\\n`);
  document.getElementById('tw').href =
    `https://twitter.com/intent/tweet?text=${{txt}}&url=${{encodeURIComponent(location.href)}}`;
  document.getElementById('score').classList.add('on');
  document.getElementById('score').scrollIntoView({{behavior:'smooth'}});
}}
document.getElementById('again').onclick = () => location.reload();
</script>
</body>
</html>
"""


def main(check_json, out_dir):
    q = json.loads(Path(check_json).read_text())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(HTML.format(
        title=q["title"], lead=q.get("lead", ""),
        n=len(q["questions"]), brand="Algo-Gym",
        data=json.dumps(q, ensure_ascii=False)))
    print(f"CHECK_OK {out/'index.html'}  {len(q['questions'])}問")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
