---
id: "ISSUE-0163"
title: "被测子进程可读到判分源码：泄漏通道是 npm 导出的 INIT_CWD/npm_package_json/PATH 与继承的 PWD，而非 PYTHONPATH；移除 PYTHONPATH 后泄漏率仅从 59% 降到 35%"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "harness_repo_path_reachable_from_subject,npm_injected_env_leaks_repo,inherited_pwd_names_repo,measurement_subject_can_read_grader"
evidence: "用 shim pi（PATH 前置脚本，dump 自身 argv+env）实测真实子进程：① ARGV 含 /Users/xbpd/Projects/researchctl-product/.pi/extensions/catalog/index.ts；② env 含 INIT_CWD、npm_config_local_prefix、npm_package_json=<repo>/package.json，PATH 含 <repo>/node_modules/.bin 与 <repo>/../node_modules/.bin；③ PWD 被继承为仓库路径而真实 cwd 是夹具。模型的实际利用方式是最朴素的一条：env | grep -i research 命中 npm_package_json，然后 read catalog/test/recovery.ts（全部场景与期望码）与 recovery-run.ts。46 行观察中 15 个场景、364 次调用引用仓库路径，例如 rec-semantic-metadata-value-not-text 的第 23 次调用直接 ls <repo> && grep src。修法：scrubbedChildEnv 删除 PYTHONPATH/INIT_CWD/所有 npm_*/PI_SESSION_*，PWD 设为子进程真实 cwd，PATH 过滤掉仓库与其父目录下的条目；并把扩展 stage 到 tmpdir（argv 不再含仓库路径，且 staged 副本不含 catalog/test，逃逸后也读不到答案）。验证：修后同一 shim 实测 argv 只含 /var/folders/.../researchctl-stage-*，env 中含仓库路径的变量为 0，staged 树无 catalog/test，且 staged 扩展能真实完成一次 research_status 调用。新增 4 个测试（含反向验证：故意还原 scrubbedChildEnv 后测试失败）"
related: []
fix_ref: null
summary: "被测子进程可读到判分源码：泄漏通道是 npm 导出的 INIT_CWD/npm_package_json/PATH 与继承的 PWD，而非 PYTHONPATH；移除 PYTHONPATH 后泄漏率仅从 59% 降到 35%"
---

## 现象

恢复测量的被测对象能定位并读取 harness 仓库：判分器源码、全部场景定义与期望错误码、以及本次实跑自己的结果文件都在可读范围内——而泄漏的主通道不是显式设置的 PYTHONPATH，是 npm run 注入的环境变量与进程继承状态，因此只删 PYTHONPATH 无法闭合

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

（待评估：影响面 / 是否有 workaround）

## 根因

（待定位）

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
