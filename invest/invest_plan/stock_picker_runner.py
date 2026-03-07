"""
每日选股文件管理模块
负责检查选股 CSV 是否存在，以及在缺失时触发后台生成。

幂等性保证：
- 每个"策略+日期"对应一个 .running 锁文件（存放后台进程 PID）
- 触发前先检查锁文件：若 PID 对应进程仍在运行则跳过，不重复 fork
- 进程结束后锁文件由子进程（通过 wrapper）自动清理
"""

import os
import sys
import subprocess
import time
from typing import Tuple, Optional

# tushare_selector 目录
_SELECTOR_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'tushare_selector')
)
# 选股输出根目录（tushare_selector/output/）
_SELECTOR_OUTPUT_ROOT = os.path.join(_SELECTOR_DIR, 'output')
# tushare_selector/main.py 路径
_SELECTOR_MAIN = os.path.join(_SELECTOR_DIR, 'main.py')


def get_csv_path(strategy_name: str, date: str, output_root: str = None) -> str:
    """
    构造期望的每日选股 CSV 文件路径

    路径规则：{output_root}/{策略名}/{策略名}_{date}.csv

    Args:
        strategy_name: 策略名称（来自策略 yaml 中的 strategy_name 字段）
        date:          选股日期 YYYYMMDD
        output_root:   选股输出根目录，默认为 tushare_selector/output/

    Returns:
        str: CSV 文件绝对路径
    """
    root = output_root or _SELECTOR_OUTPUT_ROOT
    safe_name = strategy_name.replace(' ', '_').replace('/', '_')
    return os.path.join(root, safe_name, f"{safe_name}_{date}.csv")


def _lock_path(strategy_name: str, date: str, output_root: str = None) -> str:
    """构造锁文件路径（与 CSV 同目录，后缀 .running）"""
    root = output_root or _SELECTOR_OUTPUT_ROOT
    safe_name = strategy_name.replace(' ', '_').replace('/', '_')
    lock_dir = os.path.join(root, safe_name)
    os.makedirs(lock_dir, exist_ok=True)
    return os.path.join(lock_dir, f"{safe_name}_{date}.running")


def _is_running(lock_file: str, timeout_seconds: int = 3600) -> bool:
    """
    检查锁文件对应的后台进程是否仍在运行。

    读取锁文件中的 PID，用 os.kill(pid, 0) 探测进程存活性。
    若进程已退出、锁文件无效、或锁文件超过 timeout_seconds（默认 1 小时），
    则返回 False 并清理锁文件。
    """
    if not os.path.exists(lock_file):
        return False

    # 超时检测：锁文件存在超过 timeout_seconds 则视为僵死，强制清理
    lock_age = time.time() - os.path.getmtime(lock_file)
    if lock_age > timeout_seconds:
        print(f"[stock_picker_runner] 锁文件超时（{lock_age:.0f}s > {timeout_seconds}s），强制清理：{lock_file}")
        _remove_lock(lock_file)
        return False

    try:
        with open(lock_file, 'r') as f:
            pid = int(f.read().strip())
        # os.kill(pid, 0) 不发信号，只探测进程是否存在
        os.kill(pid, 0)
        return True  # 进程仍在运行
    except (ValueError, ProcessLookupError, PermissionError):
        # PID 无效或进程已不存在，清理残留锁
        _remove_lock(lock_file)
        return False


def _remove_lock(lock_file: str) -> None:
    """安全删除锁文件"""
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
    except OSError:
        pass


def ensure_stock_pick(
    strategy_path: str,
    strategy_name: str,
    date: str,
    output_root: str = None,
) -> Tuple[bool, Optional[str], bool]:
    """
    确保指定日期的选股 CSV 文件存在。

    返回值：(exists, csv_path, just_spawned)
    - (True,  csv_path, False)：CSV 已存在
    - (False, None,     False)：后台任务已在运行，本次未重复 fork
    - (False, None,     True) ：刚刚触发了新的后台任务

    Args:
        strategy_path:  策略 yaml 的绝对路径
        strategy_name:  策略名称
        date:           选股日期 YYYYMMDD
        output_root:    选股输出根目录（默认 tushare_selector/output/）

    Returns:
        (exists: bool, csv_path: str | None, just_spawned: bool)
    """
    csv_path = get_csv_path(strategy_name, date, output_root)

    if os.path.exists(csv_path):
        return True, csv_path, False

    lock_file = _lock_path(strategy_name, date, output_root)

    if _is_running(lock_file):
        # 后台任务已在运行，无需重复 fork
        return False, None, False

    # 确定 CSV 输出目录（tushare_selector main.py 的 -o 参数）
    safe_name = strategy_name.replace(' ', '_').replace('/', '_')
    csv_output_dir = os.path.join(output_root or _SELECTOR_OUTPUT_ROOT, safe_name)

    # 触发后台子进程，写入锁文件
    _spawn_stock_picker(strategy_path, date, lock_file, output_dir=csv_output_dir)
    return False, None, True


def _spawn_stock_picker(strategy_path: str, date: str, lock_file: str,
                        output_dir: str = None) -> None:
    """
    在后台 fork 子进程执行每日选股，并写入 PID 锁文件。

    子进程结束后自动清理锁文件（通过内联 Python wrapper 实现）。

    Args:
        strategy_path: 策略 yaml 绝对路径
        date:          选股日期 YYYYMMDD
        lock_file:     锁文件绝对路径
        output_dir:    CSV 输出目录（不传则让 tushare_selector 自行决定）
    """
    # 日志文件与锁文件同目录，后缀 .log
    log_file = lock_file.replace('.running', '.log')

    # 构造选股命令参数列表（全部用 repr 序列化为字符串字面量，嵌入 wrapper_code）
    run_args = [sys.executable, _SELECTOR_MAIN, '-s', strategy_path, '-d', date]
    if output_dir:
        run_args += ['-o', output_dir]
    run_args_repr = repr(run_args)

    # 用内联 Python 脚本做 wrapper：运行选股 → 完成后删除锁文件
    wrapper_code = (
        f"import subprocess, os, sys\n"
        f"result = subprocess.run({run_args_repr},"
        f"cwd={repr(_SELECTOR_DIR)})\n"
        f"lock = {repr(lock_file)}\n"
        f"os.path.exists(lock) and os.remove(lock)\n"
    )

    with open(log_file, 'w', encoding='utf-8') as log_fp:
        proc = subprocess.Popen(
            [sys.executable, '-c', wrapper_code],
            stdout=log_fp,
            stderr=log_fp,
        )

    # 写入 PID 到锁文件
    with open(lock_file, 'w') as f:
        f.write(str(proc.pid))


def read_top_n_stocks(csv_path: str, top: int) -> list:
    """
    读取选股 CSV 文件，返回前 top 名股票信息列表

    Args:
        csv_path: CSV 文件绝对路径
        top:      取前 N 名

    Returns:
        List[dict]: 每项包含 {"code": "000001.SZ", "name": "平安银行"}
    """
    import pandas as pd

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"选股文件不存在：{csv_path}")

    # 文件为空（0字节）或只有空白内容时直接返回空列表
    if os.path.getsize(csv_path) == 0:
        return []

    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except pd.errors.EmptyDataError:
        return []

    if df.empty:
        return []

    # 列名兼容：英文列名或中文列名（save_to_csv 保存后为中文）
    code_col = None
    for candidate in ['股票代码', 'ts_code']:
        if candidate in df.columns:
            code_col = candidate
            break

    if code_col is None:
        raise ValueError(f"CSV 文件中未找到股票代码列：{csv_path}")

    name_col = None
    for candidate in ['股票名', 'name']:
        if candidate in df.columns:
            name_col = candidate
            break

    rows = df.head(top)
    result = []
    for _, row in rows.iterrows():
        item = {"code": row[code_col]}
        item["name"] = str(row[name_col]) if name_col and pd.notna(row[name_col]) else ""
        result.append(item)
    return result
