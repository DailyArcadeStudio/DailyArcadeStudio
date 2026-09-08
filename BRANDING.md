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

### ⚠ 電話番号認証が必要

**カスタムサムネはチャンネルの電話番号認証が済むまでAPIから設定できない。**
現状は403で弾かれるため、画像だけ生成して手動設定待ちに登録している。

1. https://www.youtube.com/verify で電話番号認証（DailyArcadeStudio でログイン）
2. 認証後は本編サムネがAPIから自動設定される
3. **ショートのサムネはYouTube仕様で永久にAPI不可** — 常に手動

手動設定が必要な動画は管理アプリ（`dashboard.py`）の
「⚠ 手動でサムネ設定が必要な動画」に一覧表示される。

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
