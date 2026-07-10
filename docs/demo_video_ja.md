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

> 「私は創薬の研究者で、毎日のように生医学の論文を読んでいます。『BRAF V600E の
> メラノーマは分子標的薬に反応しますか？』——LLM に聞けば、それらしい答えが返って
> きます。でも、それは本当に正しいのか。どう確かめるのか。だから作りました。
> BioClaim Auditor は、その問いに“答える”のではなく、**主張そのものを監査**します。」

---

## ② 0:15–0:55 デモ1：contested な主張（核）

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

*(豪華版：同じ主張を React Web UI（http://localhost:8000）で。強度メーター付き
verdict バナー・色分けされた Evidence Map・ダウンロードできるレポート。)*

---

## ③ 0:55–1:20 デモ2：overclaim（過剰主張）を捕まえる

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

## ④ 1:20–2:05 本番：実 PubMed（花形）＋スケール図

**画面**：3領域の比較表を一瞬映してから、vitamin D の監査
（[`outputs/example_claim_audit_vitamin_d_pubmed.md`](../outputs/example_claim_audit_vitamin_d_pubmed.md)、
キーがあれば下記をライブ実行）。

```bash
python -m biomedical_evidence_agent.cli --source pubmed \
  --claim "Vitamin D supplementation reduces the risk of cancer." \
  --top-k 6 --report claim-audit --extractor llm --reviewer claude
```

指す：**Audit Verdict: contradicted** と **VITAL** の反証行
（`hazard ratio, 0.96, 95% CI 0.88–1.06; P=0.47`）。

> 「同じツールが3領域で動きます——が、本番はここ。**実際の PubMed** に向けます。
> *“ビタミンDはがんリスクを下げる”*——多くの人が信じている主張です。監査結果は
> **contradicted（反証されている）**。ランドマークの **VITAL 試験**の“有意差なし”
> という結果を、**逐語で**引いてきます。トイデータではなく**実文献**。」

**画面**：ここで [`docs/scan_shift.svg`](scan_shift.svg) をフルスクリーンで映す
（README のスケール callout 直下。8〜10秒）。

> 「しかも一発芸ではありません。**16件の有名な主張**を実 PubMed でまとめて監査した
> 図です。中空リングがオフラインの決定論ルール、塗りつぶしが **Claude**。確立した
> 主張では**一致**しますが、雑多な実主張ではルールが破綻します——**3行**で否定済みの
> 主張を well-supported と誤判定します（**“β-カロテンが肺がんを予防”“ビタミンCが
> 風邪を予防”“変形性膝関節症の関節鏡手術は偽薬に勝る”**、いずれも実際は真逆）。
> Claude は抄録を読み、3件すべてを **contradicted** に引き戻し、ルールが取りこぼした
> 主張（セマグルチドの減量効果）はむしろ **well-supported** に救い上げます。
> “Built with Claude”は飾りではなく、**測定できる差**です。」

---

## ⑤ 2:05–2:35 Built with Claude：専門家級のレビュー

**画面**：同じ vitamin D スナップショットの **Reviewer Critique** セクション。

> 「レビュアーは **Claude**。同じエビデンスを**専門家のように**読み直します。
> がん**罹患（incidence）**については“反証”に同意しつつ、ルールが見落とした
> ニュアンス——がん**死亡（mortality）**はむしろ有益な可能性があり、あるソースが
> 誤ってラベル付けされている——を指摘します。さらに次に当たるべき試験として
> **D-Health 試験**を名指し。そして引く引用は**すべて出典と照合される**——
> だから**引用を捏造できません**。」

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
| contested な主張 | 0:40 | 判定・引用・矛盾・WWCMM |
| overclaim | 0:25 | 過剰主張フラグ＋網羅ギャップ |
| PubMed＋スケール図 | 0:45 | vitamin D 反証＋16件シフト図（Claude必然性） |
| Built with Claude | 0:30 | grounded なレビュアー・捏造引用不可 |
| 締め | 0:25 | 誠実な評価＋ピッチ＋安全 |

## 一言ピッチ（締めを短くしたい場合）

> 「BioClaim Auditor は、生命科学の主張を監査するツールです。Claude になめらかな
> 答えを出させるのではなく、**エビデンス・矛盾・引用の忠実性・次に何を調べるべきか**を
> 突きつけます。」
