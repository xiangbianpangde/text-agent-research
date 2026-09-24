---
id: "ISSUE-0186"
title: "ISSUE-0183 的修复把 auth.json 复制进子进程配置目录：16 个凭据字段（含 OAuth refresh token）可被子进程 bash 读取"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "auth_json_copied_to_child_config oauth_refresh_token_readable_by_model_tool same_process_tree_no_privilege_boundary pi_tool_is_not_a_security_domain credential_proxy_injects_real_key"
evidence: "执行者-2 零成本探针（仅 `test -r`，未读内容）先报：config_dir_set=yes、auth_file=readable。本地独立复核：以子进程身份在该 profile 下 `cat $PI_CODING_AGENT_DIR/auth.json` 成功；字段清点（仅字段名与长度）得到 16 个凭据字段，含 `xai.access/refresh`、`openai-codex.access(1700)/refresh(211)`、`antigravity.access/refresh` 及 13 个 provider 的 `key`；`grep -o` 统计返回 16，证明是**内容可读**而非仅 stat 可读。另有越出 pi 目录的路径：`~/.config/gh/hosts.yml`(GitHub token)、`~/.docker/config.json`、`~/.zshrc`、`~/.zsh_history` 在该 profile 下均可读——因 deny 只覆盖答案类路径，凭据类路径从未纳入。修复后实测：真实回合（本地 stub 上游 + redirectTo）子进程完成 response，proxy 收到 nonce，upstream 收到真实 key；子进程可见的 `*_API_KEY` 变量数 0，`~/.pi/agent/auth.json` denied，外部 egress `000DENIED`。变异验证：重新复制真实凭据文件 → preflight FAIL（`antigravity-accounts.json: a credential-bearing field holds a value that is not this run's nonce`）。"
related:
  - "ISSUE-0184"
  - "ISSUE-0185"
  - "ISSUE-0183"
fix_ref: null
summary: "ISSUE-0183 的修复把 auth.json 复制进子进程配置目录：16 个凭据字段（含 OAuth refresh token）可被子进程 bash 读取"
---

## 现象

pi 本身需要读 auth.json 才能向 provider 认证，而 pi 的 bash 工具与 pi 处于同一进程树、同一用户、同一文件权限下，因此「pi 能读的凭据，模型也能读」是结构性的，不是疏忽。为修 ISSUE-0183（子进程无法启动）而把 auth.json 复制进私有配置目录，在解决启动问题的同时把凭据放进了模型的读权限内——即修复一个缺陷的动作引入了另一个缺陷。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

模型可读取 5 个 provider 的长期凭据（含 OAuth refresh token，可换取新的 access token），并可通过其 bash 工具将内容写入任何它可达的位置。因只可追加归档不存工具输出（见 ISSUE-0185 的核查），本次未造成持久化泄漏；但可达性本身即等价于「测量装置的受试者持有装置的操作凭据」，使测量边界不再成立：无法排除模型用装置凭据访问外部资源后再答题。

## 根因

威胁模型把「不可读」定义为「答案不可读」，未包含凭据；而 pi 的 bash 工具不具备任何形式的权限降级或凭据隔离机制——它继承环境、继承文件权限、继承进程树。既然同一进程树内无法对子进程隐藏父进程必须读取的文件，唯一可行的方向就是把真实凭据移出子进程可达范围（父进程持有 + 回环代理注入）。修复过程中另暴露三个会静默使实验失效的接口缺陷：scrubbedChildEnv 忽略调用方传入的配置目录、gradingProfilePath 按单例缓存导致自有配置目录的子进程挂起（无输出/无错误/无退出码）、代理的监听 socket 使进程无法退出。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
