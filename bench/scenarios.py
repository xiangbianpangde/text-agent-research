"""ResearchCTL-Bench 32 类规范场景定义。

覆盖 8 大 Track，严格遵循《超长程实验 Agent 检索系统 Benchmark 方案 (ResearchCTL-Bench)》v1.0 规范。
"""
from __future__ import annotations

import dataclasses
from typing import Callable, List, Optional
from .evaluator import ScenarioResult


TRACKS = [
    "Track1_DefinitionProvenance",
    "Track2_RunSpecBinding",
    "Track3_ProvenanceTrace",
    "Track4_HistoricalTemporal",
    "Track5_StaleImpact",
    "Track6_IntegrityAdversarial",
    "Track7_RetrievalRouting",
    "Track8_LongHorizonContinuity",
]

TRACK_NAMES = {
    "Track1_DefinitionProvenance": "Track 1: 定义来源、依据与演化谱系",
    "Track2_RunSpecBinding": "Track 2: 实验规格与 Run 版本精确锁定",
    "Track3_ProvenanceTrace": "Track 3: 结论因果穿透与原始数据下钻",
    "Track4_HistoricalTemporal": "Track 4: 时序演化与跨报告对比",
    "Track5_StaleImpact": "Track 5: Stale 传导与逆向影响分析",
    "Track6_IntegrityAdversarial": "Track 6: 完整性巡检与对抗防御",
    "Track7_RetrievalRouting": "Track 7: 双路检索边界与防越界",
    "Track8_LongHorizonContinuity": "Track 8: 超长程科研全景重建与韧性",
}


@dataclasses.dataclass
class ScenarioDef:
    scenario_id: str
    track: str
    name: str
    description: str
    fn: Callable[..., ScenarioResult]
