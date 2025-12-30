# Pre-Live Trading Checklist

**Purpose**: Minimum mandatory steps before enabling live trading. This is not gold-plating—it's the safety floor.

---

## Applicability

| Goal | Paper Trading | Latency Benchmark | Risk Triggers | Failure Modes |
|------|---------------|-------------------|---------------|---------------|
| **Learning/Demos** | Optional | Optional | Optional | Optional |
| **Paper Trading** | ✅ Required | ✅ Strongly | ✅ Required | ✅ Strongly |
| **Live Trading** | ✅ Mandatory | ✅ Mandatory | ✅ Mandatory | ✅ Mandatory |

---

## 1. Paper Trading with IBKR ✅

**Why**: IBKR API behavior ≠ docs. Orders are async. Partial fills, rejects, delays happen.

### Minimum Test
- [ ] Run full trading day
- [ ] Place LMT orders
- [ ] Place Bracket orders (TP/SL)
- [ ] Verify: Order → Ack → Fill → Position update
- [ ] Verify: No stuck states
- [ ] Restart trading process mid-session and verify state recovery

### Pass Criteria
- [ ] All order types execute correctly
- [ ] Callbacks fire as expected
- [ ] PnL reconciles with expected values

---

## 2. Latency Benchmarking ✅

**Why**: Stale signals = wrong AI decisions by design.

### Minimum Measurements
- [ ] Market data arrival → Signal decision (P50/P95/P99)
- [ ] Signal → Order submit (P50/P95/P99)
- [ ] Order submit → IBKR ack (P50/P95/P99)

### Pass Criteria
- [ ] Latency is stable (no long tails > 2x P95)
- [ ] Worst-case < regime horizon (e.g., < 100ms for intraday)
- [ ] No unexpected spikes during market hours

---

## 3. Risk-Trigger Testing ✅

**Why**: AI systems fail silently. You must prove limits work.

### Minimum Tests
- [ ] Simulate -X% daily loss → Trading halts
- [ ] Simulate position size breach → Order rejected
- [ ] Simulate order flood → Rate limit kicks in
- [ ] Simulate market data freeze → System pauses
- [ ] Verify risk triggers are evaluated **before** order submission (pre-trade, not reactive)

### Pass Criteria
- [ ] Trading halts automatically
- [ ] Open orders canceled
- [ ] System stays down until manual restart

---

## 4. Failure-Mode Testing ✅

**Why**: Markets do not wait for retries.

### Minimum Failures to Simulate
- [ ] IBKR API disconnect mid-order
- [ ] Price = None / NaN
- [ ] Order rejected by exchange
- [ ] Delayed fills (> 30 seconds)
- [ ] Duplicate callbacks
- [ ] Clock skew / timestamp anomaly (optional but recommended)

### Pass Criteria
- [ ] System fails fast (no hangs)
- [ ] Open orders canceled on disconnect
- [ ] Trading frozen until confirmed reconnect
- [ ] Human alert triggered

---

## Final Sign-Off

Before enabling live trading:

- [ ] Paper trading completed
- [ ] Latency measured & bounded
- [ ] Risk triggers proven
- [ ] Failure modes handled

**Only then**: Enable live trading with **small capital**.

---

> ⚠️ Skipping these steps means accepting undefined behavior with real money.
