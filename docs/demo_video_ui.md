# 3-minute product demo — UI-forward narrated video (script)

This is the exact script behind the narrated 3:00 screen-recording of the React
web UI (title → problem → audit → Evidence Map + citation faithfulness →
overclaim → live PubMed × Claude → the closed-loop Resolution Path → close).

The rendered video's voice-over is Google TTS (synthesized). For a submission,
re-recording these lines in your own voice lands far better — the timings below
are what the current cut uses, so a same-paced read drops straight in.

The terminal-focused storyboards remain at [`demo_video.md`](demo_video.md)
(EN) and [`demo_video_ja.md`](demo_video_ja.md) (JA narration).

| # | Time | On screen | Narration (EN) |
|---|------|-----------|----------------|
| 0 | 0:00–0:07 | Title card | BioClaim Auditor. A Claude-powered claim-auditing tool for life sciences. |
| 1 | 0:07–0:29 | App landing (claim box) | Every day, researchers read the biomedical literature — and so do the models we build on top of it. The danger isn't failing to find an answer. It's getting a confident answer that quietly buries the disagreement underneath. BioClaim Auditor takes a different stance. It doesn't summarize a claim. It audits it. |
| 2 | 0:29–0:57 | Run audit → **contested** verdict + metrics | You give it one biological claim. Here: BRAF V600E melanoma responds to targeted inhibitor treatment. Instead of a smooth summary, it returns a graded verdict. Contested — not confirmed. One clinical study supports the claim; another, equally strong, conflicts with it. The tool surfaces that tension instead of averaging it away. |
| 3 | 0:57–1:24 | Scroll the Evidence Map + citation faithfulness | It breaks the claim into its entities — the gene, the disease, the drug class — and maps supporting versus conflicting evidence for each, with the exact sources behind them. And this is the part that matters: every cited quote is checked to be a verbatim span of its source. One hundred percent faithful. No paraphrase drift. No invented citations. |
| 4 | 1:24–1:50 | Overclaim example → red Evidence Map + flags | It flags the contradiction rather than smoothing it over. And when a claim overreaches — say, that a TP53 mutation definitively cures colorectal cancer — the auditor catches the overclaim, and shows you the entity that no retrieved evidence even addresses. The Evidence Map turns red exactly where the claim outruns its support. |
| 5 | 1:50–2:20 | `docs/scan_shift.svg` figure | This isn't a toy running on toy data. Point it at live PubMed, with Claude doing the extraction and review, and run it across sixteen known claims. On the clean ones, simple rules and Claude agree. But on the messy, real claims, the deterministic rules break — three times they even endorse claims that were later debunked. Claude lands all three correctly. Claude here isn't decoration. It's measurably load-bearing. |
| 6 | 2:20–2:46 | Resolution Path → click **Re-audit on live PubMed** | And an audit that only grades a claim stops short. BioClaim Auditor tells you how to settle it — grounded in the gaps it found, named to the claim's own entities. Sources disagree? Here's the tie-breaker to go find. And it doesn't just say it — one click re-audits on live PubMed, running the same grounded pipeline toward the evidence that would resolve it. |
| 7 | 2:46–3:00 | Closing card | Grounded. Auditable. Honest about uncertainty. BioClaim Auditor — built with Claude, for the way researchers actually read: evidence you can check, not an answer you have to trust. |

## ナレーション（日本語・自分の声で録り直す用）

- **0 (0:00–0:07)** BioClaim Auditor。Claudeを使った、ライフサイエンス向けの主張監査ツールです。
- **1 (0:07–0:29)** 研究者は日々、生物医学の文献を読みます。そしてその上に作るモデルも同じです。危険なのは、答えが見つからないことではありません。裏にある食い違いを静かに覆い隠した、自信ありげな答えが返ってくることです。BioClaim Auditor は違う立場を取ります。主張を要約するのではなく、監査します。
- **2 (0:29–0:57)** 使い方は、生物学的な主張をひとつ渡すだけ。ここでは「BRAF V600E変異のメラノーマは、標的阻害薬に反応する」。滑らかな要約の代わりに、判定を返します。Contested——確定ではなく係争中。ある臨床研究は支持し、同じくらい強い別の研究は反証しています。ツールはその緊張を平均化せず、そのまま可視化します。
- **3 (0:57–1:24)** 主張をエンティティに分解します——遺伝子、疾患、薬剤クラス。そしてそれぞれについて、支持と反証の証拠を、出典付きでマッピングします。そして重要なのはここ。引用された各文は、出典の中の逐語一致かどうかを検証します。忠実性100%。言い換えのズレも、捏造された引用もありません。
- **4 (1:24–1:50)** 矛盾は、ならすのではなくフラグを立てます。そして主張が行き過ぎたとき——例えば「TP53変異が大腸がんを確実に治す」——監査は過剰主張を検出し、取得した証拠が一切触れていないエンティティを示します。Evidence Map は、主張が根拠を追い越したまさにその場所で赤くなります。
- **5 (1:50–2:20)** これはトイデータで動くおもちゃではありません。実際のPubMedに接続し、抽出とレビューをClaudeに任せ、16の既知の主張で走らせます。きれいな主張では、単純なルールもClaudeも一致します。しかし雑然とした実際の主張では、決定的なルールが破綻します。3件では、のちに否定された主張を支持とすら判定します。Claudeは3件すべてを正しく判定します。ここでのClaudeは飾りではありません。計測可能な形で不可欠です。
- **6 (2:20–2:46)** そして、主張を判定するだけの監査は、そこで止まってしまいます。BioClaim Auditor は、どうすれば決着するかまで示します——監査が見つけたギャップに基づき、その主張のエンティティ名で。出典が食い違う? では、探すべき決め手はこれ。しかも言うだけではありません。ワンクリックで実PubMedで再監査し、同じ根拠付きパイプラインを、決着させる証拠へと走らせます。
- **7 (2:46–3:00)** 根拠がある。監査できる。不確実性に正直。BioClaim Auditor——Claudeとともに、研究者の実際の読み方のために作りました。信じるしかない答えではなく、確認できる証拠を。

## Regenerating the video

The video is assembled from generated narration + real screen recordings, all
scripted (no manual editing):

1. `scratchpad/video/narrate.py` — gTTS per-beat audio, padded, measured (defines
   timing; total lands at 3:00).
2. `web/_capture.mjs` / `_recap.mjs` (Playwright) — title/close cards, landing
   still, and the four interactive clips (audit, Evidence Map, overclaim,
   resolution loop), each recorded to its beat length.
3. `scratchpad/video/assemble.py` — trims each visual to its narration duration,
   concatenates, and muxes the voice track into a 1280×720 H.264 + AAC MP4.

Swap step 1's audio for your own voice recordings (same order/lengths) and re-run
step 3 to keep everything in sync.
