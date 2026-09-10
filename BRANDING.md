# Daily Arcade Studio — ブランディング設定シート

YouTube Studio →「カスタマイズ」で設定する項目一式。
既存3チャンネルの `develop/channels_branding.md` と同じ形式。

- **チャンネル**: https://www.youtube.com/@dailyarcadestudio
- **チャンネルID**: `UCCSFGv8ldKTepzpNm6izRQQ`
- **公開サイト**: https://dailyarcadestudio.github.io/DailyArcadeStudio/
- **ソース**: https://github.com/DailyArcadeStudio/DailyArcadeStudio

---

## 基本情報

| 項目 | 内容 |
|---|---|
| **チャンネル名** | Daily Arcade Studio |
| **ハンドル** | @dailyarcadestudio （取得済み） |
| **キャッチコピー** | A new browser game every day — free, no install |
| **カラー** | ダーク基調 `#0d1117` ＋ アクセント黄 `#d2a84c` / 青 `#58a6ff` / 赤 `#c22b35` |
| **国** | 日本 |
| **言語** | English（動画は英語ナレーション） |

---

## 画像アセット

| 用途 | サイズ | ファイル |
|---|---|---|
| アイコン | 1024x1024 | `develop/channel_icons/dailyarcadestudio.png` |
| バナー | 2560x1440 | `develop/channel_banners/dailyarcadestudio.png` |
| 動画の透かし | 150x150 | アイコンを流用（Studioで自動リサイズ） |

バナーの安全域は中央 1546x423。テキストはそこに収めてある。

再生成:
```bash
python develop/gen_arcade_icon.py    # アイコン（PIL・数秒）
python develop/gen_banners.py        # バナー（PIL・数秒）
```

アイコンは**SDXLではなくPILで描いている**。SDXLは同心円やフレームなど
余計な装飾を足してきて、48pxに縮むとノイズになるため。
`channel_icons/_dailyarcadestudio_48px_proof.png` が実寸相当の確認用。

---

## 概要（About）

```
A new browser game, every single day.

No install, no download, no launcher — every game here runs in your browser
and is free to play forever. Each video digs into one game: where the idea
came from, how the hazards are designed, and why getting hit feels the way
it does.

The link to play is always in the description, and every game stays up.
Come back tomorrow for a new one.
```

---

## キーワード（Studio → 設定 → チャンネル → キーワード）

```
browser games, free games, indie games, game dev, gamedev, three.js, webgl,
html5 games, arcade, endless runner, game design, no download games,
play in browser, daily games, indie game dev, javascript games, web games,
casual games, retro arcade, game development
```

---

## 動画メタデータの型

**タイトル**: 物語のフックを立てる（ゲーム名だけにしない）
> 例: `I Found a 1687 Complaint About Shuriken, So I Made a Game About It`

**概要欄のテンプレ**（`loop3.py` の `run_arcade` が自動生成）
```
<物語の一行>

▶ PLAY IT FREE (no install, runs in your browser):
https://dailyarcadestudio.github.io/DailyArcadeStudio/games/<slug>/

Source code for every game:
https://github.com/DailyArcadeStudio/DailyArcadeStudio

A new browser game every day on Daily Arcade Studio.

<チャプター>

#gamedev #indiegame #browsergame #threejs
```

**ショート**: タイトル末尾に `#shorts` を必ず入れる。

**タグ**: `browser game, indie game, game dev, three.js, <ゲーム固有>`

---

## サムネイル

`lib/make_thumbnail.py` が本編（1280x720）とショート（1080x1920）を自動生成する。

- 背景は**実際のゲーム画面**（`raw.mp4` から1フレーム抜く）
- 上部に**特大の煽り文句**、下に補足1行
- 文言は各ゲームの `games/<slug>/scenes.json` の `thumb` で指定:

```json
"thumb": {
  "hook": "Dodge or die",
  "sub": "3 lanes. No brakes. Free in your browser.",
  "frame_mark": "wall",
  "frame_lead": 1.0
}
```

`frame_mark` は録画のどのイベント時点を背景に使うか（`marks.json` のキー）。
夜のゲームは暗いので、`stage()` が明るさを持ち上げ、文字の帯だけ暗くしている。

### 煽り文句の言葉選び

`die` / `dead` / `kill` は**ゲームの失敗を指す動詞なら問題ない**
（"Dodge or die" / "you died" は定着したゲーム用語）。
YouTubeが問題にするのは対象が現実の人物・集団に向いている場合で、
ゲーム内の描写は広告主フレンドリー ガイドラインでも許容されている。

避けるもの:
- 実在の人物・団体を対象にした表現
- 自傷を想起させる言い回し（"kill yourself" など）
- 「Made for Kids」に設定する場合はより保守的に
  （現在は `selfDeclaredMadeForKids: False` で運用）

### 電話番号認証 ✅ 完了（2026-09-09）

カスタムサムネには電話番号認証が要る。未認証だと 403
（`doesn't have permissions to upload and set custom video thumbnails`）。
認証は https://www.youtube.com/verify で行う。

**認証後は本編・ショートとも API から設定できる。**
（当初「ショートはAPI不可」と考えていたが、実際には `thumbnails().set()` が
ショートにも通った。手動設定は不要。）

API設定が失敗した場合だけ、管理アプリ（`dashboard.py`）の
「⚠ 手動でサムネ設定が必要な動画」に積まれる。

---

## 運用

### 管理アプリ

```bash
/Users/fukushimatakumi/develop/music-llm/.venv/bin/python /Users/fukushimatakumi/develop/dashboard.py
```

「Daily Arcade (ゲーム)」ボタンで1本分を手動実行できる。
在庫日数・次のお題もこの画面に出る。

### 自動実行 ✅ 有効

**毎日 JST 4:00 に4チャンネル分が順に走る**（2026-09-09 に組み込み）。

- `daily_batch.sh`: `for ch in mosuke japanpuzzle algogym arcade`
- `loop3.py`: `ORDER = [..., "arcade"]`
- launchd: `com.algogym.dailybatch`（登録済み）

arcade は録画に headless Chromium とローカルHTTPサーバ(:8901)を使うので、
バッチの先頭で 8901 を掴んでいるプロセスを掃除している
（前回が異常終了するとポートが残るため）。

停止したいとき:
```bash
launchctl bootout gui/501/com.algogym.dailybatch     # 停止
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.algogym.dailybatch.plist  # 再開
```

**所要時間の目安**: arcade は「ゲーム生成 → 検証 → 録画 → SDXL挿絵 →
ナレーション → 動画2本 → サムネ」まで走るので、1本あたり **40〜60分**程度。
4チャンネル合計では2〜3時間かかる想定。

### 1本作る

```bash
python loop3.py --channel arcade
```

お題選択 → ゲーム生成 → **実ブラウザで動作検証** → 録画 → 挿絵 → ナレーション →
本編 → ショート → サムネ → 予約投稿（翌JST9:00）まで自動。

検証に落ちたゲームは `.built` を書かないので、次回同じお題で作り直す。

---

## 公開済み

| 日付(JST) | ゲーム | 本編 | ショート |
|---|---|---|---|
| 2026-09-09 09:00 | Ninja Dash | `B0afZ3ZNK-o` | `rJkfDBJXPrI` |

---

## 海外向け最適化（2026-09-09 設定）

### API で設定済み

| 項目 | 変更 | 効果 |
|---|---|---|
| **国 (country)** | JP → **US** | 「あなたの国の視聴者」系の推薦枠・急上昇の対象国が変わる。日本のローカル枠に入らなくなる |
| **チャンネル既定言語** | 未設定 → **en** | 未設定だと日本語話者向けに寄る。検索・推薦で英語圏に出やすくなる |

反映に20秒程度かかる（APIが成功を返した直後はまだ旧値が返る）。

```python
bs["channel"]["country"] = "US"
bs["channel"]["defaultLanguage"] = "en"
yt.channels().update(part="brandingSettings", body={"id": cid, "brandingSettings": bs})
```

### 動画側（`upload_youtube.py` が自動設定済み）

- `defaultLanguage = en` / `defaultAudioLanguage = en`
  → **これが最重要**。音声言語が未設定だと自動字幕・自動翻訳が働かず、
    英語圏の推薦にも乗りにくい。全動画で `en` を確認済み。

### Studio から手動で設定が必要（APIでは変更不可）

1. **視聴者層**: 設定 → チャンネル → 詳細設定
   - 「いいえ、子ども向けではありません」を選択（既定でそうなっているが確認）
   - **これを「子ども向け」にすると推薦・コメント・情報カードが止まる**ので要注意

2. ~~**カテゴリ**~~ → ✅ **対応済み（コード側で自動）**
   - `upload_video(..., category=)` を引数化し、arcade は **20 (Gaming)** を渡す
   - 既存4本も 27→20 に変更済み
   - 他3チャンネルは既定の 27（教育）のまま変わらない

3. **字幕**: 自動生成字幕を確認し、必要なら修正
   - 英語ナレーションなので自動生成が効く。精度が低い単語だけ直す

4. **翻訳（任意）**: 設定 → 詳細 → 「翻訳を許可」
   - タイトル・概要を多言語化すると非英語圏にも届く。
     スペイン語・ポルトガル語・ヒンディー語圏はゲーム系の視聴者が多い

### 効果が薄い / やらない方がよいもの

- **チャンネル名を英語に統一**: すでに `DailyArcadeStudio` なので不要
- **タグの大量投入**: 現在の検索アルゴリズムではほぼ効かない。
  タイトル・サムネ・概要の方が桁違いに重要
- **「国」を頻繁に変える**: 推薦の学習がリセットされうるので一度決めたら固定

---

## 公開枠の決まり方（重要）

`publish_all.next_slot()` が「最後の予約の翌日 JST 9:00」を返す。
1日1本ずつドリップして在庫を積む仕組み。

**2026-09-09 に修正**: 以前はローカルの `.schedule_state.json` だけを見ていたため、
手動アップロードや Studio での日付変更とズレると、枠が重複したり空いたりした。
（実際 Ninja Dash を手動で今日公開した結果、9/10 が空いて Lantern Drop が 9/11 になった）

現在は **YouTube 上の実際の予約を取得し、ローカルより先ならそちらを基準にする**。
取得に失敗したときだけローカルにフォールバックする。

```python
slot = P.next_slot(d, now, first_immediate=..., yt_ch=ch["yt"])
```

### サムネ未設定一覧の日付

`pending_thumbs.json` の `publish_at` は**追加した時点のスナップショット**。
あとで Studio や API で日付を変えても自動では追従しないため、
`sync_publish_dates()` で取り直す。管理アプリは起動時・10分ごと・
「🔄 更新」を押したときに自動で同期する。

```python
import pending_thumbs as PT
PT.sync_publish_dates()    # YouTube の実際の publishAt に合わせる
```

ズレを確認したいとき:
```python
import publish_all as P
P.latest_scheduled("arcade")   # YouTube 上の最後の予約
```

---

## 収益化の計画（2026-10 上旬に着手予定）

**方針**: 1ヶ月ほど自動化を回してゲームを20本以上貯めてから着手する。
コンテンツが薄いうちに AdSense へ申請しても落ちるだけなので急がない。

### 着手時にやること（この順序）

1. **Cloudflare Pages へ移行**（アカウント・ドメイン取得済み）
   - GitHub連携するだけ。ビルド設定なし（静的HTML）
   - 独自ドメインを割り当て。**AdSense は `*.github.io` では通らない**
   - `loop3.py` の `play_url` を新ドメインに変更
   - ⚠ **投稿済み動画の概要欄URLは自動では変わらない**。API で一括更新が要る
     （早く移行するほど書き換える本数が少なくて済む）

2. **各ゲームページにテキストを足す**（最重要）
   - 現状ゲームページは**本体だけでテキストがほぼゼロ**。
     クローラーからは「中身のないページ」に見え、審査で落ちる主因になる
   - `scenes.json` のナレーション原稿がそのまま使える。
     遊び方・物語・コツを本文として自動で埋め込めば、
     **ゲームが増えるほどテキストも自動で増える**

3. **必須ページを作る**
   - プライバシーポリシー（Cookie・第三者配信の記載）← AdSense が明示的に要求
   - About / お問い合わせ / 利用規約

4. **申請**（審査 1〜2週間）

### 広告サービスの選択肢

AdSense だけではない。ゲームサイトは専門サービスの方が単価も実装も有利。

| サービス | 審査 | 単価 | 備考 |
|---|---|---|---|
| AdSense | 厳しい | 中 | 独自ドメイン・コンテンツ量が必要 |
| **AdinPlay** | 中 | 高 | **HTML5ゲーム専門**。リワード/インタースティシャルが公式サポート |
| **Ezoic** | 緩い(月1万PV〜) | 高 | AI最適化 |
| Playwire | 厳しい(月50万PV〜) | 最高 | ゲーム特化 |
| PropellerAds / Adsterra | 緩い | 低〜中 | すぐ始められるが広告の質に注意 |

**AdSense と他社広告は併用可能**なので、後から足せる。

### ゲームオーバー時の広告について

やりたいのはインタースティシャル。実装上の注意:
- **リトライボタンと離して配置**（誤クリック誘導はポリシー違反）
- プレイ中には出さない
- K.O.演出が終わって操作待ちになってから表示

AdinPlay など専門サービスはこの用途が公式にサポートされている。

---

## ⚠ ショートのサムネは API から設定しない（厳守）

**2026-09-10 に実害が出た。** ショートのサムネを API で設定したところ、
YouTube は 200 を返したが反映されず、**既に設定されていたサムネを
消してしまった**。本人確認中は手動での復旧もできず、失うと戻せない。

### ガード（`upload_youtube.upload_video`）

サムネ引数が渡されても、ショートなら無視して `THUMB_BLOCKED` を出す。
判定は**タイトルの `#shorts` と、実ファイルの縦横比の両方**で行い、
**判定できないときはブロック側に倒す**（設定されない不便より、
既存サムネを消す事故のほうが高くつく）。

```python
if thumb and _is_short(path, title):
    print("THUMB_BLOCKED ...")
    thumb = None
```

上位のコードが誤って渡しても、ここで止まる。

### 運用

- ショートのサムネ**画像の生成と配置は続ける**
  → `short_thumbnails_to_set/<チャンネル>/<公開日>/short/`
- **設定は人が YouTube Studio から行う**
- 本編（16:9）は従来どおり API で設定してよい
