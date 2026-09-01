"""P1-A Evented Historical Freeze + P1-B Definition Evolution 事务子系统。

P1-A（已冻结 rev11）：freeze-report：CURRENT → REPORT-NNN + sources manifest +
  ReportFrozen Event + receipt，同一纵向事务（§3.2 固定步骤）。
P1-B（已冻结 rev11）：revise-definition：Definition@vN → vN+1 + DefinitionRevised
  Event + APPROVED pointer + receipt，18 步固定事务（§3.2）。

边界：
  - 仅操作 fixture 副本（测试）或授权项目目录；不碰真实研究目录
  - 所有 canonical 写入经本子包受控路径；plan/state/staging/marker 是派生/recovery 数据
"""
from .canonical import canonical_json, canonical_hash, canonical_hash_bytes, file_canonical_hash
from .fs import freeze_lock, install_no_clobber, write_atomic
from .ids import next_event_id, next_transaction_id, next_report_id, next_definition_version

__all__ = [
    "canonical_json", "canonical_hash", "canonical_hash_bytes", "file_canonical_hash",
    "freeze_lock", "install_no_clobber", "write_atomic",
    "next_event_id", "next_transaction_id", "next_report_id", "next_definition_version",
]
