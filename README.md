# AegisForge（白話版）

一句話：
AegisForge 幫你的 Agent 「少犯重複錯、出事時更快救回來」，而且能用數字證明有沒有變好。

-----------------------------------

## 你可以把它想成什麼？

像是 Agent 的「可靠性外掛」：
1) 記錄失敗
2) 從失敗提煉教訓
3) 下次先套用教訓
4) 自動學習哪種恢復策略最有效
5) 用 benchmark 看有沒有真的進步

-----------------------------------

## 3 分鐘上手（直接照抄）

需求：Python 3.9+

```bash
cd AegisForge

# 免安裝執行
PYTHONPATH=src python3 -m aegisforge.cli --help
```

先塞兩個常見錯誤：

```bash
PYTHONPATH=src python3 -m aegisforge.cli capture --source tool --type timeout --message "request timeout after 30s"
PYTHONPATH=src python3 -m aegisforge.cli capture --source tool --type unauthorized --message "401 unauthorized from api"
```

提煉教訓 + 注入下一輪：

```bash
PYTHONPATH=src python3 -m aegisforge.cli distill --max 3
PYTHONPATH=src python3 -m aegisforge.cli inject --top-k 3
PYTHONPATH=src python3 -m aegisforge.cli health
```

-----------------------------------

## 你最在意的：真的有感嗎？

請跑這個（預設門檻）：

```bash
PYTHONPATH=src python3 -m aegisforge.cli --root /tmp/aegisforge-qc quality-check --rounds 300
```

它會給你：
- score（滿分 10）
- 是否達標 9.0+
- adaptive 成功率
- 相對提升幅度（relative lift）

預設達標線：
- adaptive_success_rate >= 0.75
- relative_lift_pct >= 20%
- weak_lessons == 0

-----------------------------------

## Recovery Graph（最重要的新功能）

白話：
系統會學「哪個錯誤該用哪種修復策略」。

### 1) 先問系統建議怎麼修

```bash
PYTHONPATH=src python3 -m aegisforge.cli --root .aegisforge recover-plan \
  --failure-class timeout \
  --strategies retry_backoff restart_worker escalate_human
```

### 2) 修完後回報成功或失敗

```bash
PYTHONPATH=src python3 -m aegisforge.cli --root .aegisforge recover-feedback \
  --failure-class timeout \
  --strategy retry_backoff \
  --success true
```

### 3) 看學到什麼

```bash
PYTHONPATH=src python3 -m aegisforge.cli --root .aegisforge recover-report
```

-----------------------------------

## 所有命令（白話）

1) 記錯誤
- capture

2) 生教訓/用教訓
- distill
- inject
- forget
- health

3) 風險判斷
- policy（allow / ask / block）

4) 恢復學習
- recover-plan
- recover-feedback
- recover-report
- benchmark-recovery
- quality-check（9.0 驗收）

-----------------------------------

## 常見情境範例

情境 A：一直 timeout
1. recover-plan 看建議
2. 先試 retry_backoff
3. 成功就 feedback=true
4. 一週後看 report，通常會自動偏向成功率高策略

情境 B：token/權限常失敗
1. failure_class 用 unauthorized
2. strategies 放 refresh_credentials / retry_backoff / escalate_human
3. 系統會學到 refresh_credentials 成功率通常更高

情境 C：想確認這週到底有沒有進步
1. 固定每週五跑 quality-check
2. 只看三個數字：score、adaptive_success_rate、relative_lift_pct

-----------------------------------

## 資料會存哪裡？

預設在 `--root`（預設 `.aegisforge`）：
- events/error-seeds.jsonl
- lessons/active.jsonl
- lessons/snapshot.json
- recovery/graph.json
- benchmarks/...

-----------------------------------

## 版本

目前：v0.2.0

-----------------------------------

## 文件（進階）

- docs/problem-map.md
- docs/architecture.md
- docs/roadmap.md
- docs/breakthrough-poc-14d.md

-----------------------------------

## License

MIT
