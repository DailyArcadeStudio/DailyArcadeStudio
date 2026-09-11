"""動画とセットで出す「診断」ページを1枚のHTMLで作る。

構成は Daily Arcade のゲームと同じ考え方:
  - 単一HTML・外部依存なし・GitHub Pages にそのまま置ける
  - スマホ優先（タップで答える、縦画面）
  - 結果画像は SDXL が描いた「絵だけ」の画像に、文字を PIL で重ねたもの

    python make_quiz.py <quiz.json> <out_dir>

quiz.json の形は make_quiz_json.py が生成する。
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
<meta property="og:type" content="website">
<style>
  *{{box-sizing:border-box;-webkit-tap-highlight-color:transparent}}
  body{{margin:0;background:#0d1117;color:#e6edf3;
       font-family:-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;
       line-height:1.7;padding:env(safe-area-inset-top) 0 env(safe-area-inset-bottom)}}
  .wrap{{max-width:560px;margin:0 auto;padding:24px 18px 60px}}
  h1{{font-size:clamp(22px,6vw,30px);margin:8px 0 6px;line-height:1.4}}
  .lead{{color:#8b949e;font-size:15px;margin:0 0 22px}}
  .story{{background:#161b22;border-left:3px solid #ffd23b;border-radius:0 10px 10px 0;
          padding:14px 16px;margin:0 0 26px;font-size:14.5px;color:#c9d1d9}}
  .prog{{position:sticky;top:0;background:#0d1117;padding:10px 0 12px;z-index:5}}
  .bar{{height:5px;background:#21262d;border-radius:3px;overflow:hidden}}
  .bar i{{display:block;height:100%;background:#ffd23b;width:0;transition:width .25s}}
  .count{{font-size:13px;color:#8b949e;margin-top:6px}}
  .q{{margin:0 0 30px}}
  .qt{{font-size:17px;font-weight:700;margin:0 0 14px}}
  .opts{{display:grid;gap:8px}}
  .opt{{border:1px solid #30363d;background:#161b22;color:#e6edf3;border-radius:10px;
        padding:13px 14px;font-size:15px;cursor:pointer;text-align:left;
        font-family:inherit;transition:.15s}}
  .opt:active{{transform:scale(.985)}}
  .opt.on{{border-color:#ffd23b;background:#1c2128;color:#ffd23b;font-weight:700}}
  .go{{width:100%;padding:16px;border:none;border-radius:12px;background:#ffd23b;
       color:#0d1117;font-size:17px;font-weight:700;cursor:pointer;font-family:inherit;
       margin-top:8px}}
  .go:disabled{{background:#21262d;color:#6e7681;cursor:default}}
  #result{{display:none}}
  #result.on{{display:block}}
  .rimg{{width:100%;border-radius:14px;display:block;margin:0 0 18px;background:#161b22}}
  .rtype{{color:#ffd23b;font-size:14px;letter-spacing:.08em;margin:0 0 4px}}
  .rname{{font-size:clamp(24px,7vw,34px);margin:0 0 14px;line-height:1.35}}
  .rbody{{font-size:15.5px;color:#c9d1d9;margin:0 0 18px}}
  .axes{{display:grid;gap:10px;margin:0 0 24px}}
  .ax{{font-size:13px;color:#8b949e}}
  .axbar{{height:6px;background:#21262d;border-radius:3px;margin-top:5px;position:relative}}
  .axbar i{{position:absolute;top:0;height:100%;background:#58a6ff;border-radius:3px}}
  .share{{display:grid;gap:10px;margin:24px 0}}
  .share a,.share button{{display:block;text-align:center;padding:14px;border-radius:12px;
        text-decoration:none;font-weight:700;font-size:15px;border:1px solid #30363d;
        background:#161b22;color:#e6edf3;cursor:pointer;font-family:inherit}}
  .back{{display:inline-block;margin-top:8px;color:#8b949e;font-size:14px}}
  footer{{margin-top:34px;color:#6e7681;font-size:12.5px;text-align:center}}
</style>
</head>
<body>
<div class="wrap">

<div id="quiz">
  <h1>{title}</h1>
  <p class="lead">{lead}</p>
  <div class="story">{story}</div>
  <div class="prog"><div class="bar"><i id="pbar"></i></div>
    <div class="count"><span id="pnum">0</span> / {n} 問</div></div>
  <div id="qs"></div>
  <button class="go" id="submit" disabled>結果を見る</button>
</div>

<div id="result">
  <img class="rimg" id="rimg" alt="">
  <p class="rtype" id="rtype"></p>
  <h1 class="rname" id="rname"></h1>
  <p class="rbody" id="rbody"></p>
  <div class="axes" id="axes"></div>
  <div class="share">
    <a id="tw" target="_blank" rel="noopener">結果をXに投稿する</a>
    <button id="again">もう一度やる</button>
  </div>
  <a class="back" href="../../">ほかのゲーム・診断を見る</a>
</div>

<footer>{brand}</footer>
</div>

<script>
const DATA = {data};
const SCALE = ["とてもそう","ややそう","どちらとも","あまり違う","全く違う"];

const qsEl = document.getElementById('qs');
const ans = new Array(DATA.questions.length).fill(null);

DATA.questions.forEach((q, i) => {{
  const d = document.createElement('div');
  d.className = 'q';
  d.innerHTML = `<p class="qt">Q${{i+1}}. ${{q.text}}</p>`;
  const box = document.createElement('div');
  box.className = 'opts';
  SCALE.forEach((label, k) => {{
    const b = document.createElement('button');
    b.className = 'opt'; b.textContent = label;
    b.onclick = () => {{
      ans[i] = 2 - k;                    // +2(とてもそう) 〜 -2(全く違う)
      [...box.children].forEach(c => c.classList.remove('on'));
      b.classList.add('on');
      update();
    }};
    box.appendChild(b);
  }});
  d.appendChild(box);
  qsEl.appendChild(d);
}});

function update() {{
  const done = ans.filter(a => a !== null).length;
  document.getElementById('pnum').textContent = done;
  document.getElementById('pbar').style.width = (done / ans.length * 100) + '%';
  document.getElementById('submit').disabled = done < ans.length;
}}

document.getElementById('submit').onclick = () => {{
  // 軸ごとにスコアを合計する。q.axis は 0..3、q.sign は +1/-1
  const score = [0, 0, 0, 0];
  const max = [0, 0, 0, 0];
  DATA.questions.forEach((q, i) => {{
    score[q.axis] += ans[i] * q.sign;
    max[q.axis] += 2;
  }});
  // 各軸を2値にして 16 タイプのキーを作る
  const key = score.map((s, i) => s >= 0 ? DATA.axes[i].pos : DATA.axes[i].neg).join('');
  const r = DATA.results[key] || DATA.results[Object.keys(DATA.results)[0]];

  document.getElementById('rimg').src = r.image;
  document.getElementById('rimg').alt = r.name;
  document.getElementById('rtype').textContent = key;
  document.getElementById('rname').textContent = r.name;
  document.getElementById('rbody').textContent = r.body;

  const ax = document.getElementById('axes');
  ax.innerHTML = '';
  DATA.axes.forEach((a, i) => {{
    const pct = Math.round((score[i] + max[i]) / (max[i] * 2) * 100);
    const d = document.createElement('div');
    d.className = 'ax';
    d.innerHTML = `${{a.label}}<div class="axbar"><i style="left:0;width:${{pct}}%"></i></div>`;
    ax.appendChild(d);
  }});

  const txt = encodeURIComponent(`${{DATA.title}}\\n私は「${{r.name}}」でした。\\n`);
  document.getElementById('tw').href =
    `https://twitter.com/intent/tweet?text=${{txt}}&url=${{encodeURIComponent(location.href)}}`;

  document.getElementById('quiz').style.display = 'none';
  document.getElementById('result').classList.add('on');
  scrollTo(0, 0);
}};

document.getElementById('again').onclick = () => {{
  location.reload();
}};
</script>
</body>
</html>
"""


def main(quiz_json, out_dir):
    q = json.loads(Path(quiz_json).read_text())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    html = HTML.format(
        title=q["title"], lead=q.get("lead", ""), story=q.get("story", ""),
        n=len(q["questions"]), brand="Daily Arcade Studio",
        data=json.dumps(q, ensure_ascii=False))
    (out / "index.html").write_text(html)
    print(f"QUIZ_OK {out/'index.html'}  {len(q['questions'])}問 "
          f"{len(q['results'])}タイプ")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
