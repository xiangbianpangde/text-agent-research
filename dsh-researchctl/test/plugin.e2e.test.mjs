/**
 * 宿主无关端到端测试：用假 ctx 模拟 DSH loader，验证
 * 工具注册 / 真实 researchctl 调用 / 日志落盘 / research_log 聚合 /
 * 系统提示段落 / 规则误用信号。
 *
 * 运行：node --test test/plugin.e2e.test.mjs
 */

import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

import { apply, name } from '../lib/index.js'
import { WIKI_ACTION_NAMES, buildWikiArgv, extractIds } from '../lib/core/wiki.js'

const PKG_DIR = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const REPO_ROOT = path.dirname(PKG_DIR)
const FIXTURE = path.join(REPO_ROOT, 'fixture')
const HAS_FIXTURE = fs.existsSync(FIXTURE)
const HAS_WIKI_CLI = fs.existsSync(path.join(REPO_ROOT, 'tools', 'wiki.py'))

function makeCtx() {
  const tools = new Map()
  const sections = []
  const services = new Map()
  return {
    tools: { register: (tool) => tools.set(tool.name, tool) },
    get: (key) => (key === 'systemPrompt'
      ? { section: (section) => sections.push(section) }
      : undefined),
    provide: (serviceName, value) => services.set(serviceName, value),
    _tools: tools,
    _sections: sections,
    _services: services,
  }
}

function render(tool, value) {
  const blocks = tool.output.render({}, value)
  return blocks.map((block) => block.text).join('\n')
}

test('插件加载：注册三个工具 + 注入检索纪律（含 wiki 登记纪律）', () => {
  const logDir = fs.mkdtempSync(path.join(os.tmpdir(), 'researchctl-e2e-'))
  const ctx = makeCtx()
  apply(ctx, { logDir, pythonPath: process.env.RESEARCHCTL_PYTHON || 'python3' })

  assert.equal(name, 'dsh-researchctl')
  assert.deepEqual([...ctx._tools.keys()].sort(), ['research', 'research_log', 'wiki'])
  assert.equal(ctx._sections.length, 1)
  assert.equal(ctx._sections[0].name, 'dsh-researchctl:retrieval-discipline')
  assert.ok(ctx._sections[0].text.includes('层级铁律'))
  assert.ok(ctx._sections[0].text.includes('先登记、不阻塞当次任务'), '常驻纪律必须包含问题登记要求')
  assert.ok(ctx._sections[0].text.includes('不是事实证据'))
  assert.ok(ctx._services.has('researchctl'))

  const pluginLog = fs.readFileSync(path.join(logDir, 'plugin.jsonl'), 'utf8')
  assert.ok(pluginLog.includes('plugin-loaded'))
  fs.rmSync(logDir, { recursive: true, force: true })
})

test('research：真实调用 fixture 并写入调用日志', { skip: !HAS_FIXTURE }, async () => {
  const logDir = fs.mkdtempSync(path.join(os.tmpdir(), 'researchctl-e2e-'))
  const ctx = makeCtx()
  apply(ctx, { logDir, pythonPath: process.env.RESEARCHCTL_PYTHON || 'python3' })
  const research = ctx._tools.get('research')

  const value = await research.execute({ action: 'query', limit: 2 }, {})
  const text = render(research, value)
  assert.equal(value.ok, true, text)
  assert.equal(value.envelope.parsed, true)
  assert.ok(value.envelope.result_count >= 1)
  assert.ok(text.includes('[research] action=query'))

  const logFile = fs.readdirSync(logDir).find((file) => file.startsWith('calls-'))
  const rows = fs.readFileSync(path.join(logDir, logFile), 'utf8').trim().split('\n').map((line) => JSON.parse(line))
  assert.equal(rows.length, 1)
  assert.equal(rows[0].action, 'query')
  assert.equal(rows[0].layer, 'L3')
  assert.equal(rows[0].ok, true)
  assert.equal(rows[0].envelope.status, 'success')
  assert.equal(rows[0].tool, 'research')
  fs.rmSync(logDir, { recursive: true, force: true })
})

test('research：闭集动作传 semantic 会被记为规则误用（且不改执行）', { skip: !HAS_FIXTURE }, async () => {
  const logDir = fs.mkdtempSync(path.join(os.tmpdir(), 'researchctl-e2e-'))
  const ctx = makeCtx()
  apply(ctx, { logDir, pythonPath: process.env.RESEARCHCTL_PYTHON || 'python3' })
  const research = ctx._tools.get('research')

  const value = await research.execute({ action: 'sources', entity: 'CURRENT', semantic: true }, {})
  assert.equal(value.ok, true)
  assert.deepEqual(value.rule_violations, ['semantic_on_closed_command'])
  assert.ok(value.notes.some((note) => note.includes('规则误用')))
  const logFile = fs.readdirSync(logDir).find((file) => file.startsWith('calls-'))
  const row = JSON.parse(fs.readFileSync(path.join(logDir, logFile), 'utf8').trim())
  assert.equal(row.semantic_requested, true)
  assert.equal(row.layer, 'L4')
  fs.rmSync(logDir, { recursive: true, force: true })
})

test('research：参数缺失不执行，记录 bad_args 信号', async () => {
  const logDir = fs.mkdtempSync(path.join(os.tmpdir(), 'researchctl-e2e-'))
  const ctx = makeCtx()
  apply(ctx, { logDir })
  const research = ctx._tools.get('research')

  const value = await research.execute({ action: 'trace' }, {})
  assert.equal(value.ok, false)
  assert.deepEqual(value.signals, ['bad_args'])
  assert.equal(value.exit_code, null)
  const logFile = fs.readdirSync(logDir).find((file) => file.startsWith('calls-'))
  const row = JSON.parse(fs.readFileSync(path.join(logDir, logFile), 'utf8').trim())
  assert.equal(row.kind, 'bad_args')
  assert.equal(row.argv.length, 0)
  fs.rmSync(logDir, { recursive: true, force: true })
})

test('research_log：从日志聚合出统计与信号', { skip: !HAS_FIXTURE }, async () => {
  const logDir = fs.mkdtempSync(path.join(os.tmpdir(), 'researchctl-e2e-'))
  const ctx = makeCtx()
  apply(ctx, { logDir, pythonPath: process.env.RESEARCHCTL_PYTHON || 'python3' })
  const research = ctx._tools.get('research')
  const researchLog = ctx._tools.get('research_log')

  await research.execute({ action: 'query', limit: 1 }, {})
  await research.execute({ action: 'trace', entity: 'NOPE' }, {})

  const statsValue = await researchLog.execute({ scope: 'stats' }, {})
  assert.ok(statsValue.text.includes('researchctl 调用统计'))
  assert.ok(statsValue.text.includes('Fail-Closed 错误码'))
  assert.equal(statsValue.stats.totals.calls, 2)
  assert.equal(statsValue.stats.totals.fail, 1)

  const signalsValue = await researchLog.execute({ scope: 'signals' }, {})
  assert.ok(signalsValue.text.includes('fail_closed'))

  const pathsValue = await researchLog.execute({ scope: 'paths' }, {})
  assert.ok(pathsValue.text.includes(logDir))
  assert.ok(pathsValue.text.includes('analyze.js'))
  fs.rmSync(logDir, { recursive: true, force: true })
})


test('wiki 工具：只读动作可用，写动作缺 args 时报 bad_args', { skip: !HAS_WIKI_CLI }, async () => {
  assert.ok(WIKI_ACTION_NAMES.includes('issue_add') && WIKI_ACTION_NAMES.includes('suggest'))
  assert.deepEqual(buildWikiArgv('issue_list', ['--status', 'open']).argv, ['issue', 'list', '--status', 'open'])
  assert.equal(buildWikiArgv('issue_add', []).errors.length, 1)
  assert.equal(buildWikiArgv('nope', []).errors.length, 1)

  const logDir = fs.mkdtempSync(path.join(os.tmpdir(), 'researchctl-wiki-'))
  const ctx = makeCtx()
  apply(ctx, { logDir, pythonPath: process.env.RESEARCHCTL_PYTHON || 'python3' })
  const wiki = ctx._tools.get('wiki')

  assert.equal(extractIds('# 问题登记\n| ISSUE-0002 | open |').issue, null, '读取类输出不得被当成新建 ID')
  assert.equal(extractIds('OK: 已登记 ISSUE-0006 → x').issue, 'ISSUE-0006')

  const status = await wiki.execute({ action: 'status' }, {})
  assert.equal(status.ok, true, status.text)
  assert.ok(status.text.includes('ResearchCTL Wiki 看板'))

  const bad = await wiki.execute({ action: 'issue_add' }, {})
  assert.equal(bad.ok, false)
  assert.deepEqual(bad.signals, ['bad_args'])

  const logFile = fs.readdirSync(logDir).find((file) => file.startsWith('calls-'))
  const rows = fs.readFileSync(path.join(logDir, logFile), 'utf8').trim().split('\n').map((line) => JSON.parse(line))
  assert.equal(rows.length, 2)
  assert.equal(rows[0].tool, 'wiki')
  assert.equal(rows[0].action, 'wiki:status')
  assert.equal(rows[0].route, 'wiki')
  assert.equal(rows[1].kind, 'bad_args')
  fs.rmSync(logDir, { recursive: true, force: true })
})
