# ResearchCTL-Bench v0.7 P0 Harness Completion Report

> **P0 Harness Construction：COMPLETE。** 这表示评测仪器已完成 P0.1–P0.4，不表示 ResearchCTL 被认证。当前 ResearchCTL 正式结果仍未通过，Tier N/A。

## 正式 ResearchCTL 结果

| 项目 | 结果 |
| --- | --- |
| Evaluation engine | `oracle_only` |
| P0.3 status | `complete_p0_3c` |
| P0.4 status | `complete` |
| P0 status | `complete_harness` |
| Oracle coverage | 33 / 33 |
| Formal passed / failed | 6 / 27 |
| Formal composite | 20.8 / 100 |
| CIV | 0 |
| Integrity gate | FAIL |
| Certification eligibility | `false` |
| Tier | `N/A` |
| Ineligible reasons | `FORMAL_SCENARIOS_FAILED`, `INTEGRITY_GATE_FAILED` |

严格通过场景：S10、S11、S14、S19、S26、S30。Legacy 33/33 默认不运行，也不影响以上正式结果。

## P0.4 六类负控制

| 控制 | Formal PASS | Composite | CIV | Eligible | Passing conclusion |
| --- | ---: | ---: | ---: | --- | --- |
| Always-Pass | 1 / 33 | 2.1 | 0 | false | false |
| Always-Abstain | 2 / 33 | 4.2 | 0 | false | false |
| Universal-Stale | 0 / 33 | 0.0 | 6 | false | false |
| Universal-Impact | 0 / 33 | 0.0 | 6 | false | false |
| Random | 0 / 33 | 0.0 | 4 | false | false |
| Gold-Reader | 1 / 33 | 2.1 | 0 | false | false |

- Random 双跑 evaluation digest 一致。
- 官方 ResearchCTL 双跑 evaluation digest 一致：`sha256:a0a8d65261fbb267759eee3ee5b432051a88707768274f3840377ca851217cfd`。
- Gold-Reader 对 Oracle pack 的读取由 macOS sandbox 阻断。
- Attestation 绑定 manifest、33 action、source/fixture、control、adapter、executor、evaluator 与 Oracle 实现摘要。
- Attestation digest：`sha256:80b13cfa04bdce5e32ca4df0d00ec7dd44060304196bc32a6f5f441311424617`。

## P0 退出条件

- Generic runner / Oracle 对 `researchctl.*` 零 import。
- 同一进程协议测量官方 ResearchCTL 和独立 stub/control participants。
- 33/33 场景由 manifest/actions 独立编译 Gold。
- 默认路径不存在 scenario 自评分或 `run_sXX()` 调用。
- Partial、缺 Track/family、空分母不能获得 Tier。
- S12/S16/S17/S31 使用独立 evidence/set/state 判定。
- 六类负控制均无法钻过资格门。
- 官方 SUT 同 pack 双次运行得到相同 evaluation digest。

## 机器验证

- P0 Harness：56 / 56 PASS。
- ResearchCTL 原回归：443 / 443 PASS。
- Canonical source/fixture 双次重建：`sha256:205483526cf17db0066b55c0f097a99043443a79ed0c5fa919805537b73eea01`。
- Root fixture stored/fresh fingerprint：`sha256:50aef045b805311de1e1111945f1397db6fa69bb1e93b3634a6380cb3c9fc2eb`。
- Action self-award fields：0；trust-boundary ResearchCTL imports：0。

## 下一步门禁

P0 Harness 已完成，但用户原决策要求 P1/P2 只有在 P0 退出后再次批准才启动。因此当前不自动进入动态 Universe、hidden split、真实 B1/B2/B3、OCI 或排行榜治理。下一步需要用户再次批准 P1 范围。
