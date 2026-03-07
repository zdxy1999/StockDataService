"""
策略解析模块
解析YAML格式的选股策略配置
"""

import yaml
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class Operator(Enum):
    """比较操作符"""
    GT = "gt"  # 大于
    GTE = "gte"  # 大于等于
    LT = "lt"  # 小于
    LTE = "lte"  # 小于等于
    EQ = "eq"  # 等于
    NE = "ne"  # 不等于
    CONTAINS = "contains"  # 包含
    NOT_CONTAINS = "not_contains"  # 不包含


@dataclass
class FilterCondition:
    """筛选条件"""
    field: str
    operator: Operator
    value: Any

    def apply(self, data: Dict[str, Any]) -> bool:
        """应用筛选条件"""
        field_value = data.get(self.field)

        if field_value is None:
            return False

        try:
            if self.operator == Operator.GT:
                return field_value > self.value
            elif self.operator == Operator.GTE:
                return field_value >= self.value
            elif self.operator == Operator.LT:
                return field_value < self.value
            elif self.operator == Operator.LTE:
                return field_value <= self.value
            elif self.operator == Operator.EQ:
                return field_value == self.value
            elif self.operator == Operator.NE:
                return field_value != self.value
            elif self.operator == Operator.CONTAINS:
                return self.value in str(field_value)
            elif self.operator == Operator.NOT_CONTAINS:
                return self.value not in str(field_value)
            else:
                return False
        except Exception:
            return False


@dataclass
class RankingRule:
    """排名规则"""
    field: str
    order: str  # asc-升序, desc-降序
    weight: float = 1.0


@dataclass
class Strategy:
    """选股策略"""
    strategy_name: str
    filters: List[FilterCondition]
    ranking: List[RankingRule]

    def apply_filters(self, data: Dict[str, Any]) -> bool:
        """应用所有筛选条件"""
        return all(condition.apply(data) for condition in self.filters)


class StrategyParser:
    """策略解析器"""

    @staticmethod
    def parse_operator(op_str: str) -> Operator:
        """解析操作符字符串"""
        op_map = {
            "gt": Operator.GT,
            "gte": Operator.GTE,
            "lt": Operator.LT,
            "lte": Operator.LTE,
            "eq": Operator.EQ,
            "ne": Operator.NE,
            "contains": Operator.CONTAINS,
            "not_contains": Operator.NOT_CONTAINS,
        }
        return op_map.get(op_str.lower(), Operator.EQ)

    @staticmethod
    def parse_filters(filters_config: List[Dict]) -> List[FilterCondition]:
        """解析筛选条件配置"""
        filters = []
        for filter_config in filters_config:
            field = filter_config.get('field')
            operator_str = filter_config.get('operator', 'eq')
            value = filter_config.get('value')

            operator = StrategyParser.parse_operator(operator_str)

            filters.append(FilterCondition(
                field=field,
                operator=operator,
                value=value
            ))

        return filters

    @staticmethod
    def parse_ranking(ranking_config: List[Dict]) -> List[RankingRule]:
        """解析排名规则配置"""
        rules = []
        for rule_config in ranking_config:
            field = rule_config.get('field')
            order = rule_config.get('order', 'asc')
            weight = rule_config.get('weight', 1.0)

            rules.append(RankingRule(
                field=field,
                order=order,
                weight=weight
            ))

        return rules

    @staticmethod
    def parse_from_yaml(yaml_content: str) -> Strategy:
        """从YAML内容解析策略"""
        config = yaml.safe_load(yaml_content)

        strategy_name = config.get('strategy_name', '未命名策略')
        filters_config = config.get('filters', [])
        ranking_config = config.get('ranking', [])

        filters = StrategyParser.parse_filters(filters_config)
        ranking = StrategyParser.parse_ranking(ranking_config)

        return Strategy(
            strategy_name=strategy_name,
            filters=filters,
            ranking=ranking
        )

    @staticmethod
    def parse_from_file(yaml_file: str) -> Strategy:
        """从YAML文件解析策略"""
        with open(yaml_file, 'r', encoding='utf-8') as f:
            yaml_content = f.read()

        return StrategyParser.parse_from_yaml(yaml_content)
