# 每日投资功能整合
> 该文档用于整合 [投资计划](../../guoren/) 中的功能进入 StockDataService当中

## 整合目标
1. 当前的所有功能不能收到影响
2. 新功能需要以一个单独的模块存在（与原来的简单数据查询分开）
3. 整合完整的投资计划功能（但是不以命令行为入口，而是以http/mcp接口为入口）
4. 只用完成投资计划的接口，每日选股以每天定时运行的方式自动运行，不要人来触发
5. 所有的功能都要整合，包括一些实现细节：后台运行，锁，缓存等等

## 其他细节
- 保留 [投资计划](../../guoren/) 中的当前的两个plan和两个strategy作为内置的策略
- 每天定时执行所有每日选股策略（类似缓存预热）的逻辑并输出对应的csv，每个策略串行执行，但也要保留如果调用投资计划但是对应的策略结果没有的情况下马上进行后台运行的逻辑，每天定时在容器启动的配置项中指定，若未指定则默认为晚上19:30
- 所有的需要本地存储的文件（缓存文件、计算结果文件）都需要放在一个目录里面，注意通过子目录来进行分类和整理，目的是将该目录挂载出来、统一管理。

## 未整合前的启动命令
```
docker run -d \
  --name stock-data-service \
  -p 9090:9090 \
  -p 7070:7070 \
  --restart=always \
  docker.io/library/stock-data-service:x86_v1.0.10
```
需求：
1、新增一个投资策略结果定时的cron表达式
2、存储文件的挂载

## 接口设计

### 投资计划查询接口

**行为与 guoren 命令行对齐**：
- `plan_name` 可选，不指定则返回所有投资计划的结果
- `date` 可选，不指定则自动推断最新调仓日（与命令行 `--date` 逻辑一致）
- 若选股 CSV 不存在，自动在后台触发计算，接口立即返回"计算中"状态（不阻塞）

**非交易日处理逻辑**：
- 若调用方显式传入 `date`，且该日期为非交易日，接口直接返回错误，提示当天不是交易日
- 若 `date` 未传入（自动推断模式），定时任务和接口的日期推断逻辑已内置跳过非交易日，不会使用非交易日作为调仓日，无需额外处理
- 定时任务触发时（如周一到周五 19:30），若当天为节假日或非交易日，直接跳过本次执行，不触发选股

**HTTP 接口**：
```
GET /investPlan?plan_name=xxx&date=20260306
```

**MCP Tool**：
```python
def get_invest_plan(plan_name: str = None, date: str = None)
```

---

## 存储目录设计

所有需要持久化的文件统一放到一个可挂载目录（容器内路径建议 `/app/data`），挂载后可统一管理：

```
/app/data/
├── cache/                   # Tushare API 缓存（原 guoren/.cache/）
├── selector_output/         # 每日选股 CSV 结果（原 tushare_selector/output/）
│   └── {策略名}/
│       └── {策略名}_{日期}.csv
├── invest_output/           # 投资计划调仓 JSON 结果（原 invest_plan/output/）
│   └── {计划名}/
│       └── {计划名}_{日期}.json
└── logs/                    # 后台选股任务日志
    └── {策略名}/
        └── {策略名}_{日期}.log
```

---

## 定时任务设计

- **执行方式**：独立的 `scheduler.py` 进程，在 `start_servers.sh` 中与两个 Server 一同后台启动
- **触发范围**：遍历所有 `invest_plan/plans/` 下的 plan YAML，提取关联的 strategy_path，对当天日期串行触发选股
- **触发时机**：容器启动时通过环境变量 `DAILY_CRON` 指定 cron 表达式，未指定则默认 `30 19 * * 1-5`（周一至周五 19:30）
- **幂等性**：若当天 CSV 已存在则跳过，不重复计算

**Docker 启动命令调整**：
```bash
docker run -d \
  --name stock-data-service \
  -p 9090:9090 \
  -p 7070:7070 \
  -v /host/path/data:/app/data \
  -e DAILY_CRON="30 19 * * 1-5" \
  --restart=always \
  docker.io/library/stock-data-service:x86_v2.0.0
```

---

## 注意
该项目是需要docker部署的，设计需要考虑到部署的方便性


