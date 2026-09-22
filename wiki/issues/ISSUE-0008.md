---
id: "ISSUE-0008"
title: "Open-WebUI 0.11.x：未在 model 表登记的模型对非管理员完全不可见（管理员可见 → 新账号模型列表为空）"
status: "open"
severity: "medium"
area: "env"
discovered_at: "2026-09-15"
discovered_by: "agent"
tags: []
signals:
  - "empty_result"
evidence: "容器 /app/backend/open_webui/utils/models.py::get_filtered_models() 的 'elif user.role == admin: only admins can see unconfigured models' 分支；复现：POST /api/v1/auths/signup 后 GET /api/models 返回 {'data': []}；实测 model 表 0 行、access_grant 表 0 行；修复脚本 /opt/owui-publish/publish.py（登记 base_model_id=NULL 的同名覆盖行 + principal_id='*' 的公开 read 授权）；FIX-NOTES: /Users/xbpd/Projects/openwebui-student-platform/FIX-NOTES.md"
related: []
fix_ref: null
summary: "Open-WebUI 0.11.x：未在 model 表登记的模型对非管理员完全不可见（管理员可见 → 新账号模型列表为空）"
---

## 现象

新注册学生账号登录后模型下拉框为空，管理员账号一切正常；上游 OpenAI 兼容连接(api.minimaxi.com)配置正确且可达

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
