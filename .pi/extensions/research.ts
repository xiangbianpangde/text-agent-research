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
import {
	ACTIONS,
	buildArgv,
	layoutActionError,
	normalizeLayout,
	parametersSchema,
} from "../../dsh-researchctl/lib/core/actions.js";
import {
	buildResearchctlCommand,
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
		signals: ["bad_args"],
		notes,
		...extra,
	};
	return {
		content: [{ type: "text", text: JSON.stringify(details, null, 2) }],
		details,
	};
}

export default function (pi: ExtensionAPI) {
	const logger = createLogger({ source: "pi", verbose: true });

	pi.registerTool({
		name: "research",
		label: "Research State Retrieval",
		description:
			"超长程实验 Agent 检索系统（方案 §19）。用于确定性查询当前结论、依据来源、历史演化、完整性检测与派生索引维护。research-tool layout 仅允许 query/sources/trace/history/reconcile/index/generate-index；canonical 写入、事务和 bench 必须由 research-tool producer 执行。",
		parameters: parametersSchema(),
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
			if (guard) {
				const value = structuredBadArgs(action, layout, projectRoot, [guard]);
				logger.call({ tool: "research", action: action || "(missing)", route: "bad_args", layer: null, closed: false, mutating: false, layout, root: projectRoot, args: sanitizeArgs(input), argv: [], ok: false, process_ok: false, kind: "bad_args", exit_code: null, duration_ms: 0, envelope: { parsed: false }, signals: ["bad_args"], notes: [guard] });
				return value;
			}
			if (built.errors.length > 0) {
				const value = structuredBadArgs(action, layout, projectRoot, built.errors);
				logger.call({ tool: "research", action: action || "(missing)", route: "bad_args", layer: null, closed: false, mutating: false, layout, root: projectRoot, args: sanitizeArgs(input), argv: [], ok: false, process_ok: false, kind: "bad_args", exit_code: null, duration_ms: 0, envelope: { parsed: false }, signals: ["bad_args"], notes: built.errors });
				return value;
			}

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
			const { processOk, ok, kind } = outcome;
			const signals = deriveSignals({ result, summary: envelope, argv: built.argv, action, closed: ["sources", "trace", "history", "impact", "reconcile"].includes(action), semanticRequested: input.semantic === true, limitRequested: Number.isFinite(input.limit) ? Number(input.limit) : null });
			const actionSpec = ACTIONS[action];
			let parsed: unknown;
			try {
				parsed = JSON.parse(result.stdout);
			} catch {
				parsed = { raw: result.stdout, stderr: result.stderr };
			}
			const cliArgv = buildResearchctlCommand({ pythonPath: PYTHON, root: projectRoot, argv: built.argv, layout });
			const details = isRecord(parsed)
				? { ...parsed, ok, process_ok: processOk, action, layout, argv: cliArgv, kind, signals: signals.signals, notes: signals.notes }
				: { ok, process_ok: processOk, action, layout, argv: cliArgv, kind, signals: signals.signals, notes: signals.notes, envelope: parsed };
			logger.call({ tool: "research", action: action || "(missing)", route: actionSpec?.route ?? "unknown", layer: actionSpec?.layer?.(input) ?? null, closed: Boolean(actionSpec?.closed), mutating: actionSpec?.route === "mutation", layout, root: projectRoot, args: sanitizeArgs(input), argv: cliArgv, ok, process_ok: processOk, kind, exit_code: result.exitCode, duration_ms: result.durationMs, stderr_excerpt: result.stderr ? String(result.stderr).slice(0, 2000) : "", envelope, signals: signals.signals, rule_violations: signals.ruleViolations, notes: signals.notes });
			return {
				content: [{ type: "text", text: JSON.stringify(details, null, 2) }],
				details,
			};
		},
	});
}
