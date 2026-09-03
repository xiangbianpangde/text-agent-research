/**
 * research — Pi extension for researchctl (超长程实验 Agent 检索内核).
 *
 * 依据《超长程实验 Agent 检索系统设计方案.md》§19 设计：
 * 提供统一 research 工具，支持：
 *   - query: 结构化查询、词面检索与语义检索（fallback）
 *   - trace: 溯源链下钻（从结论一路到 Raw）
 *   - sources: 验证当前/历史报告来源及 exact pinned commit/hash
 *   - history: 跨历史报告追溯结论演化
 *   - impact: 逆向依赖与下游影响链分析（定义演化/实体变更影响）
 *   - reconcile: 完整性巡检（断链/篡改/漂移/孤儿文件检测）
 *   - index: 派生 SQLite 索引构建 / 全量语义重建
 */

import { execFile } from "node:child_process";
import { promisify } from "node:util";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const execFileAsync = promisify(execFile);

export default function (pi: ExtensionAPI) {
	pi.registerTool({
		name: "research",
		label: "Research State Retrieval",
		description:
			"超长程实验 Agent 检索系统（方案 §19）。用于确定性查询当前结论、依据来源、历史演化、逆向影响链与完整性检测。支持 actions: query, trace, sources, history, impact, reconcile, index。",
		parameters: Type.Object({
			action: Type.Union(
				[
					Type.Literal("query"),
					Type.Literal("trace"),
					Type.Literal("sources"),
					Type.Literal("history"),
					Type.Literal("impact"),
					Type.Literal("reconcile"),
					Type.Literal("index"),
					Type.Literal("generate-index"),
					Type.Literal("ingest-raw"),
				],
				{ description: "检索或维护动作" }
			),
			entity: Type.Optional(
				Type.String({
					description: "目标实体 ID / 引用 / 路径（用于 trace, sources, impact, 或 query --entity）",
				})
			),
			text: Type.Optional(
				Type.String({
					description: "关键词文本检索（用于 query --text）",
				})
			),
			semantic: Type.Optional(
				Type.Boolean({
					description:
						"是否启用 semantic 检索（仅作为 fallback，严禁用于替代精确 identity/version/provenance 判定）",
				})
			),
			doc_type: Type.Optional(
				Type.String({
					description: "按文档类型过滤（organized / raw / run_manifest / report_current / report_historical）",
				})
			),
			status: Type.Optional(
				Type.String({
					description: "按状态过滤（valid / invalid / completed / fresh / frozen）",
				})
			),
			raw: Type.Optional(
				Type.Boolean({
					description: "仅列出所有 raw 实体（用于 query --raw）",
				})
			),
			limit: Type.Optional(
				Type.Integer({
					description: "返回结果上限（默认 50）",
				})
			),
			change_type: Type.Optional(
				Type.String({
					description: "用于 impact 预演的语义变更类型（如 contract_tightened / upstream_scope_changed）",
				})
			),
			root: Type.Optional(
				Type.String({
					description: "研究项目根目录（默认当前工作目录）",
				})
			),
			source: Type.Optional(
				Type.String({
					description: "原始数据目录或文件路径（用于 ingest-raw）",
				})
			),
			experiment: Type.Optional(
				Type.String({
					description: "所属实验 ID（用于 ingest-raw，如 EXP-017）",
				})
			),
			run_id: Type.Optional(
				Type.String({
					description: "可选 Run ID（用于 ingest-raw，缺省自动递增分配 Rxxx）",
				})
			),
			model: Type.Optional(
				Type.String({
					description: "可选模型名称（用于 ingest-raw）",
				})
			),
			context_length: Type.Optional(
				Type.String({
					description: "可选上下文长度（用于 ingest-raw，如 128K）",
				})
			),
			seed: Type.Optional(
				Type.Integer({
					description: "可选随机种子（用于 ingest-raw）",
				})
			),
			reason: Type.Optional(
				Type.String({
					description: "可选原因说明（用于 ingest-raw 标记 invalid 时）",
				})
			),
		}),
		async execute(_id, params, _signal) {
			const projectRoot = params.root || process.cwd();
			const cmdArgs: string[] = ["-m", "researchctl", "--root", projectRoot];

			switch (params.action) {
				case "query": {
					cmdArgs.push("query");
					if (params.entity) cmdArgs.push("--entity", params.entity);
					if (params.doc_type) cmdArgs.push("--doc-type", params.doc_type);
					if (params.status) cmdArgs.push("--status", params.status);
					if (params.raw) cmdArgs.push("--raw");
					if (params.text) cmdArgs.push("--text", params.text);
					if (params.semantic) cmdArgs.push("--semantic");
					if (params.limit !== undefined) cmdArgs.push("--limit", String(params.limit));
					break;
				}
				case "trace": {
					cmdArgs.push("trace");
					if (!params.entity) {
						return {
							content: [{ type: "text", text: "Error: trace action requires 'entity' parameter." }],
							details: { ok: false, error: "entity parameter required" },
						};
					}
					cmdArgs.push(params.entity);
					break;
				}
				case "sources": {
					cmdArgs.push("sources");
					if (!params.entity) {
						return {
							content: [{ type: "text", text: "Error: sources action requires 'entity' parameter (owner ID)." }],
							details: { ok: false, error: "entity parameter required" },
						};
					}
					cmdArgs.push(params.entity);
					break;
				}
				case "history": {
					cmdArgs.push("history");
					break;
				}
				case "impact": {
					cmdArgs.push("impact");
					if (!params.entity) {
						return {
							content: [{ type: "text", text: "Error: impact action requires 'entity' parameter." }],
							details: { ok: false, error: "entity parameter required" },
						};
					}
					cmdArgs.push(params.entity);
					if (params.change_type) cmdArgs.push("--change-type", params.change_type);
					break;
				}
				case "reconcile": {
					cmdArgs.push("reconcile");
					break;
				}
				case "index": {
					cmdArgs.push("index");
					if (params.semantic) cmdArgs.push("--semantic");
					break;
				}
				case "generate-index": {
					cmdArgs.push("generate-index");
					break;
				}
				case "ingest-raw": {
					cmdArgs.push("ingest-raw");
					if (!params.experiment || !params.source) {
						return {
							content: [{ type: "text", text: "Error: ingest-raw requires both 'experiment' and 'source' parameters." }],
							details: { ok: false, error: "experiment and source parameters required" },
						};
					}
					cmdArgs.push("--experiment", params.experiment);
					cmdArgs.push("--source", params.source);
					if (params.run_id) cmdArgs.push("--run-id", params.run_id);
					if (params.status) cmdArgs.push("--status", params.status);
					if (params.model) cmdArgs.push("--model", params.model);
					if (params.context_length) cmdArgs.push("--context-length", params.context_length);
					if (params.seed !== undefined) cmdArgs.push("--seed", String(params.seed));
					if (params.reason) cmdArgs.push("--reason", params.reason);
					break;
				}
			}

			try {
				const { stdout, stderr } = await execFileAsync("python3", cmdArgs, {
					cwd: projectRoot,
					env: { ...process.env, PYTHONPATH: projectRoot },
					maxBuffer: 10 * 1024 * 1024,
				});

				let parsed: unknown;
				try {
					parsed = JSON.parse(stdout);
				} catch {
					parsed = { raw: stdout, stderr };
				}

				return {
					content: [{ type: "text", text: JSON.stringify(parsed, null, 2) }],
					details: parsed,
				};
			} catch (err: unknown) {
				const errorMsg = err instanceof Error ? err.message : String(err);
				return {
					content: [{ type: "text", text: `Execution failed: ${errorMsg}` }],
					details: { ok: false, error: errorMsg },
				};
			}
		},
	});
}
