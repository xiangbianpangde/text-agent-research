"""原子文件操作与锁（P1-A-Contract §3.6 / §4.3 / §6.2）。

- write_atomic: 临时文件 → fsync → 原子 rename → 目录 fsync
- install_no_clobber: 仅在目标不存在时安装（绝不覆盖，P1-2）
- freeze_lock: .researchctl/locks/freeze.lock（非阻塞；锁不属于可删 .index/）
- WAL 生命周期: 未提交 plan/state/staging 是唯一 recovery authority（§1.1 rule 7 / 不变量 D）
"""
from __future__ import annotations

import os
import shutil
import tempfile


class TxError(Exception):
    """P1-A 事务错误（error_semantic 透传）。"""

    def __init__(self, semantic: str, message: str):
        super().__init__(message)
        self.semantic = semantic


def write_atomic(path: str, data: bytes, fsync_dir: bool = True) -> None:
    """临时文件 → fsync → 原子 rename（覆盖式；调用方确保目标生命周期语义）。"""
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        if fsync_dir:
            try:
                dfd = os.open(d, os.O_RDONLY)
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
            except OSError:
                pass
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def install_no_clobber(path: str, data: bytes) -> bool:
    """原子 no-clobber install（§4.3）：目标已存在 → 返回 False，绝不覆盖。

    实现：对目标路径尝试 os.link(tmp, target)（原子，若目标已存在则失败）。
    失败时返回 False 并清理临时文件；成功返回 True。
    """
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(tmp, path)  # 原子 no-clobber（EEXIST 时不覆盖）
        except FileExistsError:
            os.unlink(tmp)
            return False
        try:
            dfd = os.open(d, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except OSError:
            pass
        os.unlink(tmp)
        return True
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class freeze_lock:
    """非阻塞文件锁（.researchctl/locks/freeze.lock）。获取失败返回 TxError TX_LOCKED。

    锁不在 .index/ 内（P2-7）；reindex/.index reset 必须先取同一锁（§6.2）。
    """

    def __init__(self, root: str):
        self.root = root
        self._lockdir = os.path.join(root, ".researchctl", "locks")
        self._path = os.path.join(self._lockdir, "freeze.lock")
        self._fh = None

    def acquire(self) -> None:
        os.makedirs(self._lockdir, exist_ok=True)
        import fcntl
        self._fh = open(self._path, "a+")
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._fh.close()
            self._fh = None
            raise TxError("TX_LOCKED", "另一个 freeze 事务持锁")

    def release(self) -> None:
        if self._fh is not None:
            import fcntl
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            self._fh.close()
            self._fh = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()


def is_unresolved(root: str) -> bool:
    """扫描 .index/tx 是否存在 unresolved/nonterminal WAL（§6.2 reset guard）。

    判定：存在 plan.yaml 或 staging 或 state（未到 canonical COMMITTED）。
    注意：valid receipt + 四件套验证通过的事务即使 state=needs_reconcile 也不视为 unresolved
    （P2-5：不把 canonical transaction state 与 materialization state 混合）。
    """
    from .receipt import receipt_valid_fourpiece
    from .receipt import verify_definition_receipt
    from .plan import load_plan
    from ..mini_yaml import load_file as _yaml_load
    txdir = os.path.join(root, ".index", "tx")
    if not os.path.isdir(txdir):
        return False
    any_committed = False
    for name in sorted(os.listdir(txdir)):
        if name.endswith(".plan.yaml"):
            txid = name[:-len(".plan.yaml")]
            if receipt_valid_fourpiece(root, txid):
                any_committed = True
                continue
            # P1-B: 该 plan 是否是 DefinitionRevised（四件套不适用）
            plan = load_plan(root, txid)
            if plan and "revise-definition" in plan.get("command_version", ""):
                ev_id = plan.get("event_id")
                if ev_id and verify_definition_receipt(root, ev_id).get("valid") is True:
                    any_committed = True
                    continue
            return True
    # staging 只在没有已 committed 事务且仍有残留时视为 unresolved
    staging = os.path.join(txdir, "staging")
    if not any_committed and os.path.isdir(staging) and os.listdir(staging):
        return True
    return False


def cleanup_staging(root: str) -> None:
    """清理 staging（committed 后允许；§1.1 staging 生命周期）。"""
    staging = os.path.join(root, ".index", "tx", "staging")
    if os.path.isdir(staging):
        for name in os.listdir(staging):
            p = os.path.join(staging, name)
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    os.unlink(p)
            except OSError:
                pass
