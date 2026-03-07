"""
API调用缓存管理模块
将接口调用结果缓存到本地文件，避免重复调用
"""

import os
import json
import hashlib
import pickle
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Optional
from pathlib import Path


class APICacheManager:
    """API调用缓存管理器"""

    def __init__(self, cache_dir: str = None, cache_ttl_days: int = 30):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录路径，默认为项目目录下的 .cache
            cache_ttl_days: 缓存有效期（天），默认30天
        """
        if cache_dir is None:
            # 优先使用环境变量 DATA_ROOT（Docker 挂载目录），再降级到 guoren 根目录下的 .cache
            data_root = os.environ.get('DATA_ROOT')
            if data_root:
                cache_dir = os.path.join(data_root, 'cache', 'tushare_api')
            else:
                # 默认缓存目录在项目根目录下
                project_root = Path(__file__).parent.parent
                cache_dir = project_root / '.cache' / 'tushare_api'

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_days = cache_ttl_days

    def _generate_cache_key(self, api_name: str, **kwargs) -> str:
        """
        生成缓存键

        Args:
            api_name: API名称
            **kwargs: API调用参数

        Returns:
            str: 缓存文件名（MD5哈希）
        """
        # 将参数排序后生成字符串
        params_str = json.dumps(kwargs, sort_keys=True, default=str)
        key_str = f"{api_name}:{params_str}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.pkl"

    def _get_metadata_path(self, cache_key: str) -> Path:
        """获取缓存元数据文件路径"""
        return self.cache_dir / f"{cache_key}.meta.json"

    def get(self, api_name: str, **kwargs) -> Optional[Any]:
        """
        获取缓存数据

        Args:
            api_name: API名称
            **kwargs: API调用参数

        Returns:
            缓存的数据，如果不存在或已过期则返回None
        """
        cache_key = self._generate_cache_key(api_name, **kwargs)
        cache_path = self._get_cache_path(cache_key)
        metadata_path = self._get_metadata_path(cache_key)

        # 检查缓存文件是否存在
        if not cache_path.exists() or not metadata_path.exists():
            return None

        # 检查缓存是否过期
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            cached_time = datetime.fromisoformat(metadata['cached_time'])
            if datetime.now() - cached_time > timedelta(days=self.cache_ttl_days):
                # 缓存过期，删除旧缓存
                self._remove_cache(cache_key)
                return None

            # 加载缓存数据
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)

            print(f"📦 缓存命中: {api_name} ({kwargs})")
            return data

        except Exception as e:
            print(f"⚠️  读取缓存失败: {e}")
            self._remove_cache(cache_key)
            return None

    def set(self, api_name: str, data: Any, **kwargs) -> bool:
        """
        设置缓存数据

        Args:
            api_name: API名称
            data: 要缓存的数据
            **kwargs: API调用参数

        Returns:
            bool: 是否成功
        """
        cache_key = self._generate_cache_key(api_name, **kwargs)
        cache_path = self._get_cache_path(cache_key)
        metadata_path = self._get_metadata_path(cache_key)

        try:
            # 保存数据
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)

            # 保存元数据
            metadata = {
                'api_name': api_name,
                'params': kwargs,
                'cached_time': datetime.now().isoformat(),
                'data_type': type(data).__name__
            }

            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, default=str)

            return True

        except Exception as e:
            print(f"⚠️  保存缓存失败: {e}")
            return False

    def _remove_cache(self, cache_key: str):
        """删除缓存文件"""
        cache_path = self._get_cache_path(cache_key)
        metadata_path = self._get_metadata_path(cache_key)

        try:
            if cache_path.exists():
                cache_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
        except Exception:
            pass

    def clear_expired(self):
        """清理所有过期缓存"""
        count = 0
        for metadata_file in self.cache_dir.glob("*.meta.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                cached_time = datetime.fromisoformat(metadata['cached_time'])
                if datetime.now() - cached_time > timedelta(days=self.cache_ttl_days):
                    cache_key = metadata_file.stem.replace('.meta', '')
                    self._remove_cache(cache_key)
                    count += 1

            except Exception:
                continue

        print(f"🧹 清理了 {count} 个过期缓存文件")
        return count

    def clear_all(self):
        """清理所有缓存"""
        count = 0
        for file in self.cache_dir.glob("*"):
            try:
                file.unlink()
                count += 1
            except Exception:
                continue

        print(f"🧹 清理了 {count} 个缓存文件")
        return count

    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        total_files = len(list(self.cache_dir.glob("*.pkl")))
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*"))

        return {
            'cache_dir': str(self.cache_dir),
            'total_cached_items': total_files,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'ttl_days': self.cache_ttl_days
        }
