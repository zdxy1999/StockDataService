# Changelog

## [1.1.4] - 2026-04-11

### Added
- 在所有投资计划策略中添加股价筛选条件：股价 >= 1元
- 策略1（最小流通市值策略）：添加 `close >= 1` 筛选条件
- 策略2（次新股流通策略）：添加 `close >= 1` 筛选条件

### Technical Details
- 筛选底座已支持 `close` 字段和 `gte` 操作符
- 无需修改代码，仅需在策略 YAML 文件中添加筛选条件

### Strategy Files Updated
- `invest/tushare_selector/strategies/strategy1_min_circulation_market_cap.yaml`
- `invest/tushare_selector/strategies/strategy2_new_circulation_strategy.yaml`

---

## Previous Versions

### [1.1.2] - 2026-04-11
- Initial version with price filter functionality
