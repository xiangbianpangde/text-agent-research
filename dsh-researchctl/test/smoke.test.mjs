/**
 * dsh-researchctl 核心冒烟测试（node --test）。
 * 覆盖：动作表 argv 构造 / 参数校验 / 真实 researchctl 调用 / 日志写入 / 日志聚合。
 * 运行：node --test test/
 */

import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

import { ACTION_NAMES, buildArgv, parametersSchema, usesSemantic } from '../lib/core/actions.js'
import { aggregate, parseSince, readEntries, renderStats } from '../lib/core/analyze.js'
import { createLogger } from '../lib/core/logger.js'
import { deriveSignals, runResearchctl, summarizeEnvelope } from '../lib/core/runner.js'

const PKG_DIR = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const REPO_ROOT = path.dirname(PKG_DIR)
const FIXTURE = fs.existsSync(path.join(REPO_ROOT, 'fixture')) ? path.join(REPO_ROOT, 'fixture') : null
const PYTHON = process.env.RESEARCHCTL_PYTHON || 'python3'

test('动作表：闭集动作拒绝语义检索、缺参报错、argv 顺序正确', () => {
  assert.ok(ACTION_NAMES.includes('query') && ACTION_NAMES.includes('freeze-report'))

  const layout = buildArgv('query', { entity: 'CURRENT', layout: 'research-tool' })
  assert.deepEqual(layout.argv, ['query', '--entity', 'CURRENT'])
  assert.equal(layout.errors.length, 0)

  const query = buildArgv('query', { entity: 'EXP-017', limit: 3 })
  assert.deepEqual(query.argv, ['query', '--entity', 'EXP-017', '--limit', '3'])
  assert.equal(query.layer, 'L3')
  assert.equal(query.errors.length, 0)

  const semantic = buildArgv('query', { text: 'acc', semantic: true })
  assert.equal(semantic.layer, 'L5')
  assert.ok(usesSemantic(semantic.argv))

  const trace = buildArgv('trace', { entity: 'R051', semantic: true })
  assert.equal(trace.closed, true)
  assert.equal(trace.semanticRequested, true, '误用意图必须被记录下来')
  assert.equal(usesSemantic(trace.argv), false, '闭集动作不把 --semantic 传给 CLI（会被忽略）')
  assert.deepEqual(trace.argv, ['trace', 'R051'])

  const missing = buildArgv('trace', {})
  assert.equal(missing.errors.length, 1)
  assert.equal(missing.argv.length, 0)

  const unknown = buildArgv('nope', {})
  assert.equal(unknown.errors.length, 1)

  const tx = buildArgv('revise-definition', {
    idempotency_key: 'k1', definition: 'H003', expected_previous: 'H003@v1',
    definition_input: 'd.md', actor: 'a', authorization_ref: 'r', approval_ref: 'p',
  })
  assert.ok(tx.argv.includes('--expected-previous'))
  assert.equal(tx.route, 'mutation')
})

test('research-tool layout 禁止 legacy canonical 写入动作', async () => {
  const { createExecutor } = await import('../lib/core/executor.js')
  const calls = []
  const logger = { dir: '/tmp', call: (row) => { calls.push(row); return { seq: 1 } } }
  const executor = createExecutor({ logger, resolveRoot: () => '/tmp', pythonPath: 'python3' })
  const value = await executor.research({ action: 'ingest-raw', layout: 'research-tool', experiment: 'EXP-1', source: '/tmp' })
  assert.equal(value.ok, false)
  assert.equal(value.kind, 'bad_args')
  assert.equal(calls[0].layout, 'research-tool')
})

test('参数 schema：action 必填且为闭集枚举', () => {
  const schema = parametersSchema()
  assert.deepEqual(schema.required, ['action'])
  assert.deepEqual(schema.properties.action.enum, ACTION_NAMES)
  assert.equal(schema.additionalProperties, false)
})

test('runResearchctl：真实调用 fixture，Envelope 可摘要', { skip: !FIXTURE }, async () => {
  const result = await runResearchctl({
    pythonPath: PYTHON,
    root: FIXTURE,
    moduleRoot: REPO_ROOT,
    argv: ['query', '--limit', '2'],
    timeoutMs: 60000,
  })
  assert.equal(result.ok, true, `stderr=${result.stderr}`)
  const summary = summarizeEnvelope(result.stdout)
  assert.equal(summary.parsed, true)
  assert.equal(summary.status, 'success')
  assert.ok(summary.result_count >= 1)
  assert.equal(summary.empty, false)
})

test('runResearchctl：--limit 生效且不再误报 limit_ignored（ISSUE-0001 回归）', { skip: !FIXTURE }, async () => {
  const result = await runResearchctl({
    pythonPath: PYTHON,
    root: FIXTURE,
    moduleRoot: REPO_ROOT,
    argv: ['query', '--limit', '2'],
    timeoutMs: 60000,
  })
  assert.equal(result.ok, true, `stderr=${result.stderr}`)
  const summary = summarizeEnvelope(result.stdout)
  assert.equal(summary.result_count, 2, '显式 --limit 必须真正截断')
  const signals = deriveSignals({
    result, summary, argv: ['query', '--limit', '2'], action: 'query', closed: false, limitRequested: 2,
  })
  assert.ok(!signals.signals.includes('limit_ignored'), 'limit 生效后不应再报 limit_ignored')

  const all = await runResearchctl({
    pythonPath: PYTHON, root: FIXTURE, moduleRoot: REPO_ROOT, argv: ['query'], timeoutMs: 60000,
  })
  assert.ok(summarizeEnvelope(all.stdout).result_count > 2, '缺省仍返回全量')
})

test('runResearchctl：Fail-Closed 错误被摘要为 error_codes', { skip: !FIXTURE }, async () => {
  const result = await runResearchctl({
    pythonPath: PYTHON,
    root: FIXTURE,
    moduleRoot: REPO_ROOT,
    argv: ['trace', 'NOPE'],
    timeoutMs: 60000,
  })
  const summary = summarizeEnvelope(result.stdout)
  assert.equal(summary.status, 'error')
  assert.deepEqual(summary.error_codes, ['NOT_FOUND'])
  const signals = deriveSignals({ result, summary, argv: ['trace', 'NOPE'], action: 'trace', closed: true })
  assert.ok(signals.signals.includes('fail_closed'))
})

test('deriveSignals：limit 未生效要显式告知（不静默吞意图）', () => {
  const signals = deriveSignals({
    result: { kind: 'ok', exitCode: 0, durationMs: 9, timedOut: false, truncated: false, error: null },
    summary: { parsed: true, status: 'success', error_codes: [], empty: false, result_count: 13, stale_count: 0 },
    argv: ['query', '--limit', '2'],
    action: 'query',
    closed: false,
    semanticRequested: false,
    limitRequested: 2,
  })
  assert.ok(signals.signals.includes('limit_ignored'))
  assert.ok(signals.notes[0].includes('未生效'))
})

test('deriveSignals：闭集上的 semantic 记为规则误用', () => {
  const signals = deriveSignals({
    result: { kind: 'ok', exitCode: 0, durationMs: 5, timedOut: false, truncated: false, error: null },
    summary: { parsed: true, status: 'success', error_codes: [], empty: false, drift: false, stale_count: 0 },
    argv: ['trace', 'R051', '--semantic'],
    action: 'trace',
    closed: true,
    semanticRequested: true,
  })
  assert.deepEqual(signals.ruleViolations, ['semantic_on_closed_command'])
  assert.ok(signals.signals.includes('semantic_on_closed_command'))
})

test('logger + analyze：写入后能被读取并聚合', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'researchctl-log-'))
  const logger = createLogger({ logDir: dir, source: 'dsh' })
  assert.equal(logger.enabled, true)
  logger.call({ tool: 'research', action: 'query', layer: 'L3', ok: true, kind: 'ok', duration_ms: 12, signals: [], envelope: { parsed: true, status: 'success', empty: false, result_count: 2 } })
  logger.call({ tool: 'research', action: 'trace', layer: 'L4', ok: false, kind: 'nonzero_exit', duration_ms: 30, signals: ['fail_closed'], rule_violations: ['semantic_on_closed_command'], envelope: { parsed: true, status: 'error', empty: true, result_count: 0, error_codes: ['NOT_FOUND'] } })
  logger.event('test', {})

  const read = readEntries({ logDir: dir })
  assert.equal(read.entries.length, 2)
  assert.equal(read.parseErrors, 0)

  const stats = aggregate(read.entries, read)
  assert.equal(stats.totals.calls, 2)
  assert.equal(stats.totals.fail, 1)
  assert.equal(stats.error_codes.NOT_FOUND, 1)
  assert.equal(stats.rule_violations.semantic_on_closed_command, 1)
  assert.equal(stats.totals.empty, 1)
  assert.equal(stats.by_layer.L3.ok, 1, '分层/来源/日期桶也要记成功失败')
  assert.equal(stats.by_source.dsh.calls, 2)
  assert.equal(stats.by_day[Object.keys(stats.by_day)[0]].calls, 2)
  assert.ok(renderStats(stats).includes('Fail-Closed 错误码'))

  assert.ok(parseSince('24h') < Date.now())
  assert.equal(parseSince('7d') !== null, true)
  fs.rmSync(dir, { recursive: true, force: true })
})
