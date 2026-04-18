# MEMORY

## 2026-04-19

- Retry/backoff 不能只處理 happy path，空 backoff 輸入要自動正規化，避免錯誤處理流程再崩潰。
- LLM fallback 需要可觀測，至少要持續追蹤 retry 次數、fallback 比例、錯誤分類，否則無法評估穩定性。
- 發佈流程要有 gate 與 rollback 文件，避免只靠口頭約定導致高風險版本直接進入 Hermes 生產路徑。
