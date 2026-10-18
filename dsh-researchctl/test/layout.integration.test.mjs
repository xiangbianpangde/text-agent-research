/**
 * research-tool layout acceptance tests for the DSH core contract.
 *
 * The Python fixture is created by the isolated worktree's own strict
 * research-tool test helper. No main-worktree tools/wiki.py is consulted.
 */

import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

import { buildArgv, layoutActionError, parametersSchema } from '../lib/core/actions.js'
import { createExecutor } from '../lib/core/executor.js'
import { createLogger } from '../lib/core/logger.js'
import {
  buildResearchctlCommand,
  classifyEnvelope,
  runResearchctl,
  summarizeEnvelope,
} from '../lib/core/runner.js'

const PKG_DIR = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const REPO_ROOT = path.dirname(PKG_DIR)
const PYTHON = process.env.RESEARCHCTL_PYTHON || '/opt/anaconda3/bin/python3'
const STRICT_FIXTURE_HELPER = path.join(REPO_ROOT, 'researchctl', 'tests', 'test_research_tool_layout.py')
const ACCEPTANCE_AGENT_DIR = '/Users/xbpd/Projects/research-tool/research-output/researchctl-integration-acceptance/agent-tests'

function pythonEnv() {
  return {
    ...process.env,
    PYTHONPATH: [REPO_ROOT, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
    PYTHONDONTWRITEBYTECODE: '1',
  }
}

function hasStrictFixtureHelper() {
  if (!fs.existsSync(STRICT_FIXTURE_HELPER)) return false
  const probe = spawnSync(
    PYTHON,
    ['-c', 'from researchctl.tests.test_research_tool_layout import create_fixture; print("ready")'],
    { cwd: REPO_ROOT, env: pythonEnv(), encoding: 'utf8' },
  )
  return probe.status === 0 && probe.stdout.trim().endsWith('ready')
}

const HAS_STRICT_FIXTURE = hasStrictFixtureHelper()
const FIXTURE_SKIP = HAS_STRICT_FIXTURE
  ? false
  : `strict research-tool fixture helper unavailable in isolated worktree (${PYTHON}); not treated as product pass`

function makeLogger() {
  const logDir = fs.mkdtempSync(path.join(os.tmpdir(), 'researchctl-layout-log-'))
  return { logDir, logger: createLogger({ logDir, source: 'dsh' }) }
}

function createStrictFixture() {
  const script = [
    'from researchctl.tests.test_research_tool_layout import create_fixture',
    'print(create_fixture(two_topics=False, include_failures=False))',
  ].join('; ')
  const result = spawnSync(PYTHON, ['-c', script], {
    cwd: REPO_ROOT,
    env: pythonEnv(),
    encoding: 'utf8',
  })
  assert.equal(result.status, 0, `fixture creation failed: ${result.stderr}`)
  return result.stdout.trim().split(/\r?\n/).at(-1)
}

function createResearchExecutor(root, logger) {
  return createExecutor({
    logger,
    pythonPath: PYTHON,
    moduleRoot: REPO_ROOT,
    resolveRoot: () => root,
    timeoutMs: 60000,
    maxBufferBytes: 16 * 1024 * 1024,
  })
}

function readCurrentRunId(root) {
  const runSummary = JSON.parse(fs.readFileSync(path.join(root, 'alpha', 'run-summary.json'), 'utf8'))
  return runSummary.run_id
}

function currentManifest(root, runId) {
  return JSON.parse(fs.readFileSync(path.join(root, 'alpha', 'runs', runId, 'retrieval-manifest.json'), 'utf8'))
}

test('layout schema and shared argv: default legacy, research-tool passes layout/root/topic', () => {
  const schema = parametersSchema()
  assert.deepEqual(schema.properties.layout.enum, ['legacy', 'research-tool'])

  const legacy = buildArgv('query', { entity: 'CURRENT' })
  assert.deepEqual(legacy.argv, ['query', '--entity', 'CURRENT'])
  assert.deepEqual(buildResearchctlCommand({ pythonPath: 'python3', root: '/tmp/project', argv: legacy.argv }),
    'python3 -m researchctl --layout legacy --root /tmp/project query --entity CURRENT'.split(' '))

  const researchTool = buildArgv('query', { layout: 'research-tool', topic: 'alpha', limit: 1 })
  assert.deepEqual(researchTool.argv, ['query', '--topic', 'alpha', '--limit', '1'])
  assert.deepEqual(buildResearchctlCommand({
    pythonPath: PYTHON,
    root: '/tmp/research-output',
    argv: researchTool.argv,
    layout: 'research-tool',
  }), [PYTHON, '-m', 'researchctl', '--layout', 'research-tool', '--root', '/tmp/research-output', 'query', '--topic', 'alpha', '--limit', '1'])
  assert.equal(layoutActionError('ingest-raw', 'research-tool')?.includes('禁止执行'), true)
})

test('research-tool fixture: successful query preserves layout, full argv, log summary, and process_ok', { skip: FIXTURE_SKIP }, async () => {
  const root = createStrictFixture()
  const { logDir, logger } = makeLogger()
  const executor = createResearchExecutor(root, logger)

  const indexed = await executor.research({ action: 'index', layout: 'research-tool', root })
  assert.equal(indexed.ok, true, indexed.text)
  assert.equal(indexed.process_ok, true)
  assert.equal(indexed.layout, 'research-tool')
  assert.deepEqual(indexed.argv.slice(0, 5), [PYTHON, '-m', 'researchctl', '--layout', 'research-tool'])
  assert.equal(indexed.argv[5], '--root')
  assert.equal(indexed.argv.at(-1), 'index')

  const value = await executor.research({ action: 'query', layout: 'research-tool', root, topic: 'alpha', limit: 1 })
  assert.equal(value.ok, true, value.text)
  assert.equal(value.process_ok, true)
  assert.equal(value.layout, 'research-tool')
  assert.equal(value.envelope.parsed, true)
  assert.equal(value.envelope.status, 'success')
  assert.ok(value.envelope.result_count >= 1)
  assert.deepEqual(value.argv.slice(0, 5), [PYTHON, '-m', 'researchctl', '--layout', 'research-tool'])
  assert.deepEqual(value.argv.slice(-5), ['query', '--topic', 'alpha', '--limit', '1'])

  const files = fs.readdirSync(logDir).filter((name) => name.startsWith('calls-'))
  assert.equal(files.length, 1)
  const rows = fs.readFileSync(path.join(logDir, files[0]), 'utf8').trim().split('\n').map((line) => JSON.parse(line))
  assert.equal(rows.length, 2)
  assert.ok(rows.every((row) => row.layout === 'research-tool'))
  assert.ok(rows.every((row) => row.argv[0] === PYTHON && row.argv.includes('--layout') && row.argv.includes('research-tool')))
  assert.equal(rows.at(-1).args.layout, 'research-tool')

  fs.rmSync(logDir, { recursive: true, force: true })
})

test('research-tool fixture: stale read and hash-mismatch reindex are both ok=false with process_ok=true', { skip: FIXTURE_SKIP }, async () => {
  const root = createStrictFixture()
  const { logDir, logger } = makeLogger()
  const executor = createResearchExecutor(root, logger)
  const indexed = await executor.research({ action: 'index', layout: 'research-tool', root })
  assert.equal(indexed.ok, true, indexed.text)

  const runId = readCurrentRunId(root)
  const manifest = currentManifest(root, runId)
  const rawPath = manifest.sources[0].raw_path.replace(`runs/${runId}/`, '')
  const raw = path.join(root, 'alpha', 'runs', runId, rawPath)
  fs.appendFileSync(raw, '\nagent-test source hash edit\n')

  const stale = await executor.research({ action: 'sources', layout: 'research-tool', root, entity: `report:alpha:${runId}` })
  assert.equal(stale.ok, false, stale.text)
  assert.equal(stale.process_ok, true)
  assert.equal(stale.kind, 'fail_closed')
  assert.equal(stale.envelope.status, 'fail_closed')
  assert.equal(stale.envelope.error_semantic, 'INDEX_STALE')
  assert.ok(stale.signals.includes('fail_closed'))

  const repairedIndex = await executor.research({ action: 'index', layout: 'research-tool', root })
  assert.equal(repairedIndex.ok, false, repairedIndex.text)
  assert.equal(repairedIndex.process_ok, true)
  assert.equal(repairedIndex.kind, 'fail_closed')
  assert.equal(repairedIndex.envelope.status, 'fail_closed')
  assert.equal(repairedIndex.envelope.error_semantic, 'HASH_MISMATCH')
  assert.ok(repairedIndex.signals.includes('fail_closed'))

  assert.ok(fs.existsSync(raw))
  fs.rmSync(logDir, { recursive: true, force: true })
})

test('research-tool fixture: all canonical writes, transactions, bench, and unsupported impact are bad_args without execution', { skip: FIXTURE_SKIP }, async () => {
  const root = createStrictFixture()
  const { logDir, logger } = makeLogger()
  const executor = createResearchExecutor(root, logger)
  const actions = [
    ['ingest-raw', { experiment: 'EXP-1', source: root }],
    ['freeze-report', { idempotency_key: 'k', actor: 'agent', authorization_ref: 'auth' }],
    ['revise-definition', {
      idempotency_key: 'k', definition: 'H003', expected_previous: 'H003@v1', definition_input: 'input.yaml',
      actor: 'agent', authorization_ref: 'auth', approval_ref: 'approval',
    }],
    ['tx-status', {}],
    ['tx-reconcile', {}],
    ['tx-reset-guard', {}],
    ['bench', {}],
    ['impact', { entity: 'anything' }],
  ]

  for (const [action, extra] of actions) {
    const value = await executor.research({ action, layout: 'research-tool', root, ...extra })
    assert.equal(value.ok, false, `${action} unexpectedly ok`)
    assert.equal(value.process_ok, false, `${action} unexpectedly executed`)
    assert.equal(value.kind, 'bad_args')
    assert.equal(value.layout, 'research-tool')
    assert.deepEqual(value.signals, ['bad_args'])
    assert.match(value.text, /research-tool/)
  }

  const files = fs.readdirSync(logDir).filter((name) => name.startsWith('calls-'))
  const rows = fs.readFileSync(path.join(logDir, files[0]), 'utf8').trim().split('\n').map((line) => JSON.parse(line))
  assert.equal(rows.length, actions.length)
  assert.ok(rows.every((row) => row.kind === 'bad_args' && row.ok === false && row.process_ok === false && row.argv.length === 0))
  fs.rmSync(logDir, { recursive: true, force: true })
})

test('legacy regression: omitted layout remains legacy and legacy write action is not layout-blocked', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'researchctl-legacy-'))
  fs.mkdirSync(path.join(root, 'reports'), { recursive: true })
  fs.writeFileSync(path.join(root, 'reports', 'CURRENT.md'), '# Legacy\n\nlegacy fixture\n')
  const { logDir, logger } = makeLogger()
  const executor = createResearchExecutor(root, logger)

  const indexed = await executor.research({ action: 'index', root })
  assert.equal(indexed.ok, true, indexed.text)
  assert.equal(indexed.layout, 'legacy')
  assert.equal(indexed.argv[0], PYTHON)
  assert.deepEqual(indexed.argv.slice(0, 7), [PYTHON, '-m', 'researchctl', '--layout', 'legacy', '--root', root])

  const ingested = await executor.research({
    action: 'ingest-raw',
    root,
    experiment: 'EXP-LEGACY',
    source: path.join(root, 'reports', 'CURRENT.md'),
  })
  assert.notEqual(ingested.kind, 'bad_args', 'legacy ingest must not be rejected by research-tool layout guard')
  assert.equal(ingested.layout, 'legacy')

  fs.rmSync(root, { recursive: true, force: true })
  fs.rmSync(logDir, { recursive: true, force: true })
})

test('shared Envelope classifier: parsed error/fail_closed keeps process_ok=true', () => {
  for (const status of ['error', 'fail_closed']) {
    const summary = summarizeEnvelope(JSON.stringify({ status, errors: [{ code: 'INDEX_STALE' }], results: [] }))
    const value = classifyEnvelope({ ok: false, kind: 'nonzero_exit' }, summary)
    assert.equal(value.ok, false)
    assert.equal(value.processOk, true)
    assert.equal(value.kind, 'fail_closed')
  }
})
