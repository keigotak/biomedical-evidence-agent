# 3分デモ動画 台本（日本語ナレーション版）

英語版は [`demo_video.md`](demo_video.md)。ビート構成・尺・コマンドは共通で、
ナレーションだけ日本語（話し言葉）にしたものです。画面に映すコマンドや出力の
ラベルは英語のままで問題ありません（ナレーションで補います）。

**収録前**：ターミナルの文字を大きく、`cd` でリポジトリへ、画面をクリア。
最短は **`bash scripts/demo.sh`**（各ビートで Enter 送り。PubMed と Claude の
ビートは保存済みスナップショットを表示するので、ネットも API キーも不要）。

---

## ① 0:00–0:15 フック

**画面**：README トップのヒーロー画像、またはタイトル「BioClaim Auditor」。

> 「『BRAF V600E のメラノーマは分子標的薬に反応しますか？』——LLM に聞けば、
> それらしい答えが返ってきます。でも、それは本当に正しいのか。どう確かめるのか。
> BioClaim Auditor は、その問いに“答える”のではなく、**主張そのものを監査**します。」

---

## ② 0:15–1:00 デモ1：contested な主張（核）

**画面**：実行してレポートをゆっくりスクロール。

```bash
python -m biomedical_evidence_agent.cli \
  --claim "BRAF V600E melanoma is associated with response to targeted inhibitor treatment." \
  --top-k 3 --report claim-audit --reviewer mock
```

指す順：**Audit Verdict: contested → Supporting / Conflicting Evidence →
Citation Audit 2/2 verbatim → Contradiction flag → What Would Change My Mind**。

> 「判定は **contested（見解が割れている）**——支持する臨床エビデンスが1件、
> 相反するものが1件。引用した文は、すべて出典に**一言一句そのまま存在するか
> 検証済み**です。矛盾を覆い隠さず**フラグとして提示**し、“何が分かればこの結論が
> 変わるか”まで示します。」

*(豪華版：同じ主張を Streamlit UI で。verdict バッジ・色付き Evidence Map・
ダウンロードできるレポート。)*

---

## ③ 1:00–1:30 デモ2：overclaim（過剰主張）を捕まえる

```bash
python -m biomedical_evidence_agent.cli \
  --claim "TP53 mutation definitively cures colorectal cancer with salbutamol." \
  --top-k 3 --report claim-audit
```

指す：**🔴 Overclaim flag**（`cures`・`definitively` が `insufficient` の判定に
不釣り合い）と、**Evidence Map** の
`colorectal cancer … ⚠ no evidence addresses this entity`。

> 「今度は、エビデンスを超えた言い回しを与えます——**“definitively cures”
> （決定的に治す）**。すると **overclaim フラグ**が立ちます。Evidence Map は
> 主張をエンティティ単位に分解し、**“大腸がん”に触れている証拠が一つも無い**ことを
> 可視化します。言葉の“盛り”を見逃しません。」

---

## ④ 1:30–2:00 汎化＋実文献

**画面**：比較表、続いて PubMed スナップショット。

```bash
python experiments/compare_claims.py
```

> 「同じツールが、**腫瘍・免疫・神経の3領域**で動きます——contested が2つ、
> well-supported が1つ、overclaim が1つ、**一覧で**把握できます。」

続いて [`outputs/example_claim_audit_pubmed.md`](../outputs/example_claim_audit_pubmed.md)
を開く（ネットが使えるなら `--source pubmed` を実行）。

> 「しかも**トイデータ専用ではありません**。実際の **PubMed** に向ければ、
> 本物の論文を監査し、**実試験からの逐語引用付き**で well-supported を返します。」

---

## ⑤ 2:00–2:35 Built with Claude

**画面**：[`outputs/example_claim_audit_claude_reviewer.md`](../outputs/example_claim_audit_claude_reviewer.md)
を開く（キーがあれば `--reviewer claude`）。BRIM-3 の行を強調。

> 「このレビュアーは **Claude 自身**です。カードを**懐疑的に読み直し**、ここでは
> “ヘッジした言い回し”を指摘し、**“durable（持続的）”と“initial（初期）”の反応を
> 区別**し、決定的な **BRIM-3 試験**を次に当たるべき文献として挙げます。そして
> Claude が引く引用は**すべて出典と照合される**——だから**引用を捏造できません**。
> BRIM-3 の提案に引用が付いていないのは、その論文がコーパスに無いからです。」

*(任意：`experiments/reviewer_duel.py --mode claude` = advocate・skeptic・judge
の三者が論戦、いずれも grounded。)*

---

## ⑥ 2:35–3:00 締め：誠実さ＋ピッチ

**画面**：`python -m biomedical_evidence_agent.evaluation` の末尾（stress 8/9、
extractor ablation）または [`docs/evaluation.md`](evaluation.md)、最後に安全カード。

> 「**限界にも正直**です——**7系統の評価**、真の値 **8/9** で報告する stress セット、
> そして引用ガードが**“素朴な抽出器を救い、注意深いモデルには透明である”**ことを
> 示す ablation。狙いはこうです——Claude に**なめらかな答え**を求めるのではなく、
> **エビデンス・不確実性・矛盾・引用の忠実性・次の検証項目**を、モデルに晒させる。
> あくまで**研究のためのシグナル**であり、**医療アドバイスではありません**。」

---

## 尺の早見表

| ビート | 尺 | 見せるもの |
|---|---|---|
| フック | 0:15 | 何であって何でないか |
| contested な主張 | 0:45 | 判定・引用・矛盾・WWCMM |
| overclaim | 0:30 | 過剰主張フラグ＋網羅ギャップ |
| 汎化＋PubMed | 0:30 | 3領域＋実論文 |
| Built with Claude | 0:35 | grounded なレビュアー・捏造引用不可 |
| 締め | 0:25 | 誠実な評価＋ピッチ＋安全 |

## 一言ピッチ（締めを短くしたい場合）

> 「BioClaim Auditor は、生命科学の主張を監査するツールです。Claude になめらかな
> 答えを出させるのではなく、**エビデンス・矛盾・引用の忠実性・次に何を調べるべきか**を
> 突きつけます。」
