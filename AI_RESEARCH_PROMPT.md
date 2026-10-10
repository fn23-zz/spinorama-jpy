# AIエージェント向け 日本市場価格 確からしさ調査・自動更新プロンプト

このガイドは、AIエージェント（Antigravity, Claude Code, Cursor, またはWeb検索機能を持つLLMエージェント）にスピーカーの日本国内市場価格を高精度に調査させ、本データベースへ直接反映させるためのプロンプトおよび作業仕様書です。

---

## 1. AIエージェントにそのまま投げる指示プロンプト（コピペ用）

以下のテキストブロックをそのままAIエージェントにプロンプトとして入力してください。

```markdown
あなたは音響機器（スピーカー）の日本国内市場調査の専門家エージェントです。
作業フォルダは `/home/nari/scripts/spinorama_JPY` です。

### 目的
過去の機械的推計により誤りが多く含まれる日本国内のスピーカー価格データを正しく精査し、
最新かつ最も確からしい市場価格（1本価格・ペア価格）、流通状況、および根拠をデータベースに反映してください。

### 提供されているCLIツール
本プロジェクトにはエージェント専用の検証CLIが用意されています。
1. 未検証スピーカーの取得:
   python3 backend/agent_verifier.py list --limit 5 --priority cpi_desc
   （priorityは cpi_desc / score_desc / brand_asc から選択可能）

2. 単一スピーカーの詳細取得:
   python3 backend/agent_verifier.py get <SPEAKER_ID>

3. 調査結果のデータベース反映（検証保存・CPI自動再計算）:
   python3 backend/agent_verifier.py save --json '<JSON文字列>'
   または
   python3 backend/agent_verifier.py save --json path/to/result.json

---

### 【最重要】調査時の厳格な判定ルール

調査結果の精度を極限まで高めるため、以下の4つのルールを必ず順守してください。

#### ルール1: 「1本売り」か「ペア（2本組）売り」かを徹底的に判別せよ
- モニタースピーカー（Genelec, JBL Professional, Yamaha HS, ADAM, Neumann, Focal Pro等）は、基本的に「1本（1台）」単位で販売されています。
- ピュアオーディオ向けスピーカー（KEF, B&W, DALI, JBL家庭用等）は通常「ペア販売」ですが、定価表示が「1本あたり（ペア販売のみ）」と記載されている落とし穴があります。
- 1本価格が分かった場合は `price_each` に設定し、ペア価格 `price_jpy = price_each * 2` を計算してください。ペア価格が分かった場合はその半額を `price_each` としてください。

#### ルール2: 部品・アクセサリー・スタンドを本体価格と誤認するな
- 検索結果に数千円〜数万円でヒットする「専用スピーカースタンド」「壁掛けブラケット」「交換用サランネット」「補修用ウーファーユニット」はスピーカー本体ではありません。誤ってこれを価格として登録しないでください。

#### ルール3: 「国内流通なし（海外限定/DIY/入手困難）」の判定
- Audio Science Review (ASR) 発のDIYキット（Directiva, CSS等）や、日本国内に正規代理店が存在しない海外ガレージブランド、海外Kickstarter限定品は【国内流通なし】と判定してください。
- 国内流通なしの場合：
  - `availability: "not_available"`
  - `verification_status: "unavailable"`
  - `price_jpy: null`
  - `price_each: null`
  ※為替換算価格を無理やり残さず、必ず `null`（価格不明）にしてください。

#### ルール4: 信頼性の高い情報源
- サウンドハウス (soundhouse.co.jp)
- 価格.com (kakaku.com)
- ヨドバシカメラ / ビックカメラ
- Amazon.co.jp（公式ストア・国内正規代理店出品）
- 各ブランドの国内正規輸入代理店公式サイト（ジェネレックジャパン、ハーマンインターナショナル、D&M等）

---

### 実行手順

1. `python3 backend/agent_verifier.py list --limit 5 --priority cpi_desc` を実行して、未検証の対象スピーカーを取得する。
2. 各スピーカーについて、提供された `search_queries` やモデル名・ブランド名をもとにWeb検索を実行する。
3. 検索結果から以下を特定する：
   - 国内正規流通の有無（あるか / 並行輸入のみか / 流通なしか）
   - 販売価格（税込。1本単価、およびペア換算価格）
   - 参照した情報源（店舗名・サイト名、およびURL）
   - 備考（1本売りであることの明記、国内代理店名、モデルの補足など）
4. 以下の形式のJSONを作成し、`python3 backend/agent_verifier.py save` でDBに保存する。

#### 保存用JSONフォーマット
```json
{
  "speaker_id": 371,
  "price_jpy": 140800,
  "price_each": 70400,
  "price_type": "pair",
  "availability": "domestic_in_stock",
  "verification_status": "verified",
  "confidence_level": "high",
  "source_name": "サウンドハウス / ジェネレックジャパン",
  "source_url": "https://www.soundhouse.co.jp/products/detail/item/...",
  "search_keyword": "Genelec G Two 価格",
  "notes": "1本あたり70,400円 (ペア換算140,800円)。国内正規品。"
}
```

※国内流通なしの場合の例：
```json
{
  "speaker_id": 10,
  "availability": "not_available",
  "verification_status": "unavailable",
  "confidence_level": "high",
  "source_name": "国内正規代理店なし確認",
  "notes": "日本国内での正規輸入代理店および市販流通なし（海外直販/DIY限定）。価格不明。"
}
```

5. 指定件数の調査・保存が完了したら、`python3 backend/export_static.py` を実行して静的データも最新化し、完了報告を行ってください。
```

---

## 2. 反映ルートの確認

AIエージェントが結果をデータベースに反映するルートは2種類あります。どちらも完全に対応しています。

### ルートA: CLIスクリプト経由（推奨・安全）
- コマンド: `python3 backend/agent_verifier.py save --json '{...}'`
- 特徴:
  - バックエンドサーバーの起動状態に関係なく動作。
  - SQLiteのWALモードで安全にトランザクション処理。
  - 保存と同時にコスパ指標（CPI: `cp_tone` 等）の回帰分析・再計算を全自動実行。

### ルートB: ローカルHTTP API経由
- エンドポイント: `POST http://127.0.0.1:8550/api/verification/save`
- ヘッダー: `Content-Type: application/json`
- ボディ: 上記と同じJSON構造
- 特徴:
  - 外部のRESTクライアントやcurl、Pythonの `requests` から直接呼び出し可能。
  - 画面（http://narivl:8550）を開いている場合、WebSocketやポーリングにより即座に反映。
