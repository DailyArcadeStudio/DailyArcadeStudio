"""歴史シミュレータのページを1枚のHTMLで作る。

「あなたがその人物だったら」を12回の2択で進め、4つの結末のどれかに着く。
判定は2軸のパラメータ蓄積（4象限）。分岐ツリーにすると結末が爆発するため。

史実と違う結末にも行ける。シミュレータなのでそれでよいが、
**史実ではない旨を必ず画面に出す**（音声合成の規約で「嘘やフェイク」は不可）。

    python make_sim.py <sim.json> <out_dir>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HTML = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<meta property="og:title" content="{title}">
<meta property="og:description" content="{lead}">
<style>
  *{{box-sizing:border-box;-webkit-tap-highlight-color:transparent}}
  body{{margin:0;background:#0b0e14;color:#e6edf3;
       font-family:-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;
       line-height:1.75;padding:env(safe-area-inset-top) 0 env(safe-area-inset-bottom)}}
  .wrap{{max-width:600px;margin:0 auto;padding:22px 18px 60px}}
  h1{{font-size:clamp(21px,5.6vw,29px);margin:6px 0 8px;line-height:1.4}}
  .lead{{color:#8b949e;font-size:14.5px;margin:0 0 20px}}
  .prog{{position:sticky;top:0;background:#0b0e14;padding:10px 0 12px;z-index:5}}
  .bar{{height:4px;background:#1c2333;border-radius:2px;overflow:hidden}}
  .bar i{{display:block;height:100%;background:#d4a544;width:0;transition:width .3s}}
  .count{{font-size:12.5px;color:#8b949e;margin-top:6px;letter-spacing:.04em}}
  .scene{{background:#121722;border:1px solid #222b3d;border-radius:14px;
          padding:20px 18px;margin:0 0 16px}}
  .year{{color:#d4a544;font-size:12.5px;letter-spacing:.1em;margin:0 0 8px}}
  .sit{{font-size:16px;margin:0 0 18px;color:#dbe3ec}}
  .opts{{display:grid;gap:10px}}
  .opt{{border:1px solid #2b3550;background:#161d2b;color:#e6edf3;border-radius:11px;
        padding:15px 16px;font-size:15.5px;cursor:pointer;text-align:left;
        font-family:inherit;line-height:1.6;transition:.15s}}
  .opt:hover{{border-color:#d4a544}}
  .opt:active{{transform:scale(.985)}}
  .log{{margin:0 0 20px}}
  .logi{{border-left:2px solid #2b3550;padding:2px 0 2px 14px;margin:0 0 10px;
         font-size:13.5px;color:#7d8796}}
  .logi b{{color:#b3bdcc;font-weight:600}}
  #end{{display:none}} #end.on{{display:block}}
  .eimg{{width:100%;border-radius:14px;display:block;margin:0 0 18px;background:#121722}}
  .etag{{color:#d4a544;font-size:13px;letter-spacing:.09em;margin:0 0 4px}}
  .ename{{font-size:clamp(23px,6.4vw,32px);margin:0 0 14px;line-height:1.35}}
  .ebody{{font-size:15.5px;color:#c9d1d9;margin:0 0 20px;white-space:pre-wrap}}
  .fact{{background:#121722;border-left:3px solid #58a6ff;border-radius:0 10px 10px 0;
         padding:14px 16px;margin:0 0 20px;font-size:14.5px;color:#c9d1d9}}
  .fact b{{color:#58a6ff;display:block;margin-bottom:5px;font-size:12.5px;
           letter-spacing:.08em}}
  .warn{{color:#6e7681;font-size:12.5px;margin:18px 0 0;padding:12px 14px;
         border:1px dashed #2b3550;border-radius:10px}}
  .share{{display:grid;gap:10px;margin:22px 0}}
  .share a,.share button{{display:block;text-align:center;padding:14px;border-radius:12px;
        text-decoration:none;font-weight:700;font-size:15px;border:1px solid #2b3550;
        background:#161d2b;color:#e6edf3;cursor:pointer;font-family:inherit}}
  .back{{display:inline-block;margin-top:6px;color:#8b949e;font-size:14px}}
  footer{{margin-top:32px;color:#6e7681;font-size:12.5px;text-align:center}}
</style>
</head>
<body>
<div class="wrap">

<div id="sim">
  <h1>{title}</h1>
  <p class="lead">{lead}</p>
  <div class="prog"><div class="bar"><i id="pbar"></i></div>
    <div class="count"><span id="pnum">1</span> / {n}</div></div>
  <div class="log" id="log"></div>
  <div class="scene" id="scene"></div>
</div>

<div id="end">
  <img class="eimg" id="eimg" alt="">
  <p class="etag" id="etag"></p>
  <h1 class="ename" id="ename"></h1>
  <p class="ebody" id="ebody"></p>
  <div class="fact" id="fact"></div>
  <div class="share">
    <a id="tw" target="_blank" rel="noopener">結果をXに投稿する</a>
    <button id="again">やり直す</button>
  </div>
  <a class="back" href="../">ほかのシミュレータを見る</a>
  <p class="warn">これはシミュレータです。あなたの選択によっては史実と異なる結末になります。
  実際に起きたことは上の「史実」の欄をご覧ください。</p>
</div>

<footer>{brand}</footer>
</div>

<script>
const DATA = {data};
let i = 0;
const score = [0, 0];
const picks = [];

const sceneEl = document.getElementById('scene');
const logEl = document.getElementById('log');

function render() {{
  const s = DATA.scenes[i];
  document.getElementById('pnum').textContent = i + 1;
  document.getElementById('pbar').style.width = (i / DATA.scenes.length * 100) + '%';
  sceneEl.innerHTML = `<p class="year">${{s.year}}</p><p class="sit">${{s.situation}}</p>`;
  const box = document.createElement('div');
  box.className = 'opts';
  s.options.forEach(o => {{
    const b = document.createElement('button');
    b.className = 'opt';
    b.textContent = o.text;
    b.onclick = () => choose(o);
    box.appendChild(b);
  }});
  sceneEl.appendChild(box);
}}

function choose(o) {{
  score[0] += o.a || 0;
  score[1] += o.b || 0;
  picks.push(o.text);
  const d = document.createElement('div');
  d.className = 'logi';
  d.innerHTML = `<b>${{DATA.scenes[i].year}}</b> ${{o.text}}`;
  logEl.appendChild(d);
  i++;
  if (i < DATA.scenes.length) {{ render(); scrollTo(0, 0); }}
  else finish();
}}

function finish() {{
  // 2軸の符号で4象限 → 4つの結末
  const key = (score[0] >= 0 ? DATA.axes[0].pos : DATA.axes[0].neg)
            + (score[1] >= 0 ? DATA.axes[1].pos : DATA.axes[1].neg);
  const e = DATA.endings[key] || DATA.endings[Object.keys(DATA.endings)[0]];
  document.getElementById('eimg').src = e.image;
  document.getElementById('eimg').alt = e.name;
  document.getElementById('etag').textContent = e.tag || 'ENDING';
  document.getElementById('ename').textContent = e.name;
  document.getElementById('ebody').textContent = e.body;
  document.getElementById('fact').innerHTML =
    `<b>史実では</b>${{DATA.history}}`;
  const txt = encodeURIComponent(
    `${{DATA.title}}\\n私の結末は「${{e.name}}」でした。\\n`);
  document.getElementById('tw').href =
    `https://twitter.com/intent/tweet?text=${{txt}}&url=${{encodeURIComponent(location.href)}}`;
  document.getElementById('sim').style.display = 'none';
  document.getElementById('end').classList.add('on');
  scrollTo(0, 0);
}}

document.getElementById('again').onclick = () => location.reload();
render();
</script>
</body>
</html>
"""


def main(sim_json, out_dir):
    q = json.loads(Path(sim_json).read_text())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(HTML.format(
        title=q["title"], lead=q.get("lead", ""),
        n=len(q["scenes"]), brand="MosukeStudio",
        data=json.dumps(q, ensure_ascii=False)))
    print(f"SIM_OK {out/'index.html'}  {len(q['scenes'])}場面 "
          f"{len(q['endings'])}結末")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
