# AegisForge

AegisForge 是一個開源「代理人可靠性作業層（Agent Reliability OS）」。

它不是要取代 Claude Code、GPT Codex、OpenClaw、Hermes Agent；
而是把這四個生態最強的能力整合成一個可落地、可驗證、可擴充的統一層。

一句話：
讓 AI 代理人「不只會做事」，還能「越做越穩、越錯越少、跨通道一致」。

## 為什麼要做 AegisForge

現在主流代理人都有亮點，但企業/個人落地時還是卡在同一批痛點：

1. 重複犯錯
- 這次修過，下次又踩同坑。

2. 記憶失控
- 記憶一直長，品質卻沒保證；噪音越積越多。

3. 安全邊界不明
- 自動化很強，但破壞性行為缺乏硬性閘門。

4. 跨平台割裂
- CLI、Telegram、WhatsApp、Slack 等通道行為不一致。

5. 無法量化改進
- 「看起來變聰明」不等於真的更可靠，缺少可比較指標。

AegisForge 目標就是把這些痛點變成可工程化解決的問題。

## 四大生態的優點，怎麼整合

### Claude Code（借鏡）
- 高品質的 coding 迭代節奏
- 對開發任務的執行穩定性

AegisForge 吸收：
- 工程任務導向流程
- 高頻迭代中的錯誤回收機制

### GPT Codex（借鏡）
- 任務拆解與程式生成速度
- 快速原型與修補能力

AegisForge 吸收：
- 任務分解 + 實作回圈的速度導向
- 代碼生成到驗證的閉環

### OpenClaw（借鏡）
- 多通道 Gateway（Telegram/WhatsApp/Slack/Discord...）
- 實務導向的個人助理運營模型

AegisForge 吸收：
- 多通道事件整合
- 通道級路由與操作連續性

### Hermes Agent（借鏡）
- Tool-first orchestration
- Skills / Memory / Cron / Delegation 的組合能力

AegisForge 吸收：
- 工具與技能層可插拔架構
- 可沉澱與可重用的流程資產

## 核心設計原則

1) Code-enforced Reliability
- 關鍵可靠性行為放在程式與策略層，不靠 prompt 祈禱。

2) Learn + Forget
- 會學習，也會遺忘：避免記憶膨脹與知識腐敗。

3) Observable by default
- 每個關鍵決策都可追蹤、可重播、可審計。

4) Pluggable by design
- 模型、工具、通道、策略都可替換。

5) Human override for risk
- 高風險操作一定有核准與回滾策略。

## 架構總覽

AegisForge 分成五層：

Layer 1: Event Fabric
- 統一接收 tool call、channel message、session lifecycle、failure/retry 事件。

Layer 2: Reliability Harness
- failure-capture：抓錯誤種子
- lesson-distill：萃取可執行教訓
- lesson-router：下次任務注入最相關經驗
- forgetting-engine：去重、衰減、淘汰
- integrity-check：資料一致性與品質檢查

Layer 3: Safety & Policy
- secrets 掃描
- prompt injection 掃描
- destructive action 閘門（allow/block/ask）

Layer 4: Runtime Adapters
- CLI adapter
- Messaging adapters（Telegram/WhatsApp/Slack/Discord...）
- Provider adapters（多模型供應商）

Layer 5: Evaluation & Ops
- 錯誤重複率、首次成功率、恢復步數
- 追蹤 lesson 命中率與淘汰率
- 回放與除錯工具

## MVP（v0.1）功能範圍

1. Error Capture Pipeline
- 從工具失敗、會話失敗、通道錯誤寫入 error-seeds。

2. Lesson Distillation + Injection
- 每次 session 結束萃取 1~3 條 lessons。
- 下次開始按關聯度注入 top-K。

3. Active Forgetting
- stale decay（過久未命中降權/刪除）
- LRU eviction
- semantic dedup

4. Safety Guardrail
- secrets/injection 內容攔截
- 高風險操作策略化決策（allow/block/ask）

5. Evaluation Harness
- 固定測試集做 before/after 對比
- 產生可分享報告

## 成功指標（公開可驗證）

- 重複錯誤率下降（Error Recurrence Rate）
- 任務首次成功率上升（First-pass Success）
- 平均恢復步數下降（Recovery Steps）
- 記憶命中品質上升且總量受控（Memory Hit Quality + Bounded Size）

## 專案結構

- docs/problem-map.md
  - 四大生態痛點地圖與整合策略

- docs/architecture.md
  - 元件責任與資料契約

- docs/roadmap.md
  - 階段性開發與驗收標準

- src/（規劃中）
  - 參考實作

## 路線圖（摘要）

Phase 0：事件模型與基準量測
Phase 1：學習閉環（捕捉→蒸餾→注入）
Phase 2：遺忘與品質控制
Phase 3：安全閘門
Phase 4：OSS 發佈與 benchmark 套件

## 適用場景

- 想把 AI 代理人從 demo 變成可長期運營系統
- 需要跨多通道保持一致行為
- 需要可審計的安全策略與風險控制
- 需要可以量化比較的可靠性改進

## 非目標

- 不做四大產品的「替代品」
- 不複製品牌或 UI
- 不綁定單一模型供應商

## 目前狀態

- 已完成：架構藍圖、痛點映射、MVP roadmap
- 進行中：參考實作（v0.1）

## 參與貢獻

請見 CONTRIBUTING.md。

重點歡迎：
- 能量化提升可靠性的 patch
- Lesson 品質判定與去重策略
- 多通道事件標準化與回放工具

## License

MIT
