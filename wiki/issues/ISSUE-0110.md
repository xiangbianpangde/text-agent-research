---
id: "ISSUE-0110"
title: "v75 archive-mode attestation still accepts an extra file added to artifacts map"
status: "fixed"
severity: "critical"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "attestation_archive_declared_extra_key_bypass_v75"
evidence: "archive review_v75.zip SHA-256 69af7f75096a08df5c3620987be822357a0635718cbc2a2e59e5313b805ae259; commit 6adead09423679ee45e984b91b4480cb1bdf54f4; /tmp/r61_v75_archive_declared_extra_probe.out SHA-256 5e1cf58d56d190ed81602a67d50a84e17db020ce1058a16dc129dadcfe7bf450; tools/attestation_policy.py:504-563"
related: []
fix_ref: "41fe134"
summary: "v75 archive-mode attestation still accepts an extra file added to artifacts map"
updated_at: "2026-09-22"
---

## 现象

在无 git archive 中新增 `extra_attested.txt`，并把其正确 digest 加入 artifacts map（required_set_digest 保持独立期望值）后，`--expected-required-set-digest sha256:82da...` 仍返回 rc=0、宣称 1917 paths closed。archive branch 校验 stray against declared_keys，但未校验 declared_keys 与独立 required path set 相等；攻击者可把未在 target tree 的文件同时加入 map，绕过额外文件闭包。

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

## 处置记录 2026-09-22T19:28:39+0800

追加更直接反例：删除 package/`workers/echo_worker.py`，同时从 artifacts map 删除其 key，保留独立 required_set_digest；archive verifier 仍 rc=0，宣称 1915 paths closed。证据 /tmp/r61_v75_archive_declared_missing_probe.out SHA-256 045319e863329af9e41cedaad2d12537152d6dfaf8abe5ec4be4f67484872f10。故 archive branch 同时可接受 required path omission 与 declared extra，digest 本身未提供成员集合闭包。

## 处置记录 2026-09-22T19:47:24+0800

Both the reviewer's declared-extra and declared-missing probes are now REFUSED against the shipped archive (review_v77.zip SHA 7de9414f, bound commit 468d9fc0). Root cause was the ISSUE-0103 bug class again: archive mode compared the expected digest against the required_set_digest FIELD -- a value inside the file under test -- instead of the declared map it claims to summarise, so the digest proved nothing about membership. The pin is now re-derived from the declared map (required_set_digest(declared)) and compared, and the summary field must equal that re-derivation too. Verified: extra -> 'declared field ... != ... re-derived from the declared map'; missing -> same class of refusal; unmutated archive still verifies with field == derived, so the refresh flow is unaffected. Regression tests test_archive_mode_rejects_extra_file_added_to_the_declared_map (+ paired control) and test_declared_map_digest_must_match_its_own_summary_field; mutating back to the field-only comparison fails exactly the declared-extra test.
