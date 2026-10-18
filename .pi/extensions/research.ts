/**
 * research — Pi extension for researchctl (超长程实验 Agent 检索内核).
 *
 * CLI argv / layout guard / Envelope status semantics are shared with the DSH
 * plugin through dsh-researchctl/lib/core/*.js.  Keep this adapter thin: the
 * host only supplies the tool schema and renders the structured result.
 */

import path from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import {
	ACTIONS,
	buildArgv,
	layoutActionError,
	normalizeLayout,
} from "../../dsh-researchctl/lib/core/actions.js";
import {
	classifyEnvelope,
	deriveSignals,
	runResearchctl,
	summarizeEnvelope,
} from "../../dsh-researchctl/lib/core/runner.js";
import { createLogger, sanitizeArgs } from "../../dsh-researchctl/lib/core/logger.js";

const MODULE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const PYTHON = process.env.RESEARCHCTL_PYTHON || "python3";

const isRecord = (value: unknown): value is Record<string, unknown> =>
	typeof value === "object" && value !== null && !Array.isArray(value);

function structuredBadArgs(
	action: string,
	layout: string | null,
	root: string,
	notes: string[],
	extra: Record<string, unknown> = {},
) {
	const details = {
		ok: false,
		process_ok: false,
		action: action || null,
		layout,
		root,
		kind: "bad_args",
		exit_code: null,
		argv: [],
		notes,
		...extra,
	};
	return {
		content: [{ type: "text", text: JSON.stringify(details, null, 2) }],
		details,
	};
}

export default function (pi: ExtensionAPI) {
	pi.registerTool({
		name: "research",
		label: "Research State Retrieval",
		description:
			"超长程实验 Agent 检索系统（方案 §19）。用于确定性查询当前结论、依据来源、历史演化、完整性检测与派生索引维护。research-tool layout 仅允许 query/sources/trace/history/reconcile/index/generate-index；canonical 写入、事务和 bench 必须由 research-tool producer 执行。",
		parameters: Type.Object({
			layout: Type.Optional(
				Type.Union([
					Type.Literal("legacy"),
					Type.Literal("research-tool"),
				], { description: "canonical 输出布局；默认 legacy。" })
			),
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
					Type.Literal("freeze-report"),
					Type.Literal("revise-definition"),
					Type.Literal("tx-status"),
					Type.Literal("tx-reconcile"),
					Type.Literal("tx-reset-guard"),
					Type.Literal("bench"),
				],
				{ description: "检索、维护、事务或评测动作；research-tool layout 会拒绝写入/事务/bench。" }
			),
			entity: Type.Optional(
				Type.String({ description: "目标实体 ID / 引用 / 路径。" })
			),
			text: Type.Optional(
				Type.String({ description: "关键词文本检索（用于 query --text）。" })
			),
			semantic: Type.Optional(
				Type.Boolean({ description: "是否启用 semantic 检索；不得替代身份/版本/provenance 判定。" })
			),
			doc_type: Type.Optional(
				Type.String({ description: "按文档类型过滤。" })
			),
			status: Type.Optional(
				Type.String({ description: "按状态过滤。" })
			),
			raw: Type.Optional(
				Type.Boolean({ description: "仅列出 raw 实体。" })
			),
			limit: Type.Optional(Type.Integer({ description: "返回结果上限。" })),
			topic: Type.Optional(Type.String({ description: "research-tool topic_slug 过滤。" })),
			as_of: Type.Optional(Type.String({ description: "history 的 UTC ISO 截止时刻。" })),
			change_type: Type.Optional(Type.String({ description: "impact 预演的语义变更类型。" })),
			commit: Type.Optional(Type.String({ description: "index 使用的 git commit 引用（legacy）。" })),
			root: Type.Optional(Type.String({ description: "研究项目根目录（默认当前工作目录）。" })),
			source: Type.Optional(Type.String({ description: "ingest-raw 原始数据目录或文件路径。" })),
			experiment: Type.Optional(Type.String({ description: "ingest-raw 所属实验 ID。" })),
			run_id: Type.Optional(Type.String({ description: "ingest-raw 可选 Run ID。" })),
			experiment_ref: Type.Optional(Type.String({ description: "ingest-raw 实验规格版本。" })),
			model: Type.Optional(Type.String({ description: "ingest-raw 模型名称。" })),
			context_length: Type.Optional(Type.String({ description: "ingest-raw 上下文长度。" })),
			seed: Type.Optional(Type.Integer({ description: "ingest-raw 随机种子。" })),
			reason: Type.Optional(Type.String({ description: "写入动作的原因说明。" })),
			idempotency_key: Type.Optional(Type.String({ description: "事务幂等键。" })),
			actor: Type.Optional(Type.String({ description: "事务执行者标识。" })),
			authorization_ref: Type.Optional(Type.String({ description: "事务授权引用。" })),
			approval_ref: Type.Optional(Type.String({ description: "定义修订审批引用。" })),
			reason_refs: Type.Optional(Type.String({ description: "事务原因引用列表。" })),
			definition: Type.Optional(Type.String({ description: "revise-definition 目标定义 ID。" })),
			expected_previous: Type.Optional(Type.String({ description: "定义修订期望前驱版本。" })),
			definition_input: Type.Optional(Type.String({ description: "定义修订输入文件。" })),
			crash_after: Type.Optional(Type.String({ description: "测试故障注入点。" })),
			track: Type.Optional(Type.String({ description: "bench Track。" })),
			scenario: Type.Optional(Type.String({ description: "bench 场景 ID。" })),
			save_json: Type.Optional(Type.String({ description: "bench 结果保存路径。" })),
			timeout_seconds: Type.Optional(Type.Number({ description: "本次调用超时秒数。" })),
		}),
		async execute(_id, params, _signal) {
			const input = params as Record<string, any>;
			const action = typeof input.action === "string" ? input.action.trim() : "";
			const projectRoot = typeof input.root === "string" && input.root.trim() !== ""
				? input.root.trim()
				: process.cwd();
			const layout = normalizeLayout(input.layout);
			const built = buildArgv(action, input);
			const guard = layout === null
				? `layout 必须是 legacy 或 research-tool（收到 ${String(input.layout)}）。`
				: layoutActionError(action, layout);
			if (guard) return structuredBadArgs(action, layout, projectRoot, [guard]);
			if (built.errors.length > 0) return structuredBadArgs(action, layout, projectRoot, built.errors);

			const result = await runResearchctl({
				pythonPath: PYTHON,
				root: projectRoot,
				moduleRoot: MODULE_ROOT,
				argv: built.argv,
				layout,
				timeoutMs: Number.isFinite(input.timeout_seconds) && input.timeout_seconds > 0
					? Math.floor(input.timeout_seconds * 1000)
					: 180000,
				signal: _signal,
			});
			const envelope = summarizeEnvelope(result.stdout);
			// A parsed fail-closed envelope proves the CLI ran, even when the CLI
			// deliberately exits non-zero. Keep that transport fact separate.
			const outcome = classifyEnvelope(result, envelope);
			const { processOk, ok } = outcome;
			let parsed: unknown;
			try {
				parsed = JSON.parse(result.stdout);
			} catch {
				parsed = { raw: result.stdout, stderr: result.stderr };
			}
			const details = isRecord(parsed)
				? { ...parsed, ok, process_ok: processOk, action, layout, argv: ["-m", "researchctl", "--layout", layout, "--root", projectRoot, ...built.argv] }
				: { ok, process_ok: processOk, action, layout, argv: built.argv, envelope: parsed };
			return {
				content: [{ type: "text", text: JSON.stringify(details, null, 2) }],
				details,
			};
		},
	});
}
