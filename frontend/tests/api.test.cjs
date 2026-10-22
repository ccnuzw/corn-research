const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const { resolve } = require('node:path')
const test = require('node:test')
const vm = require('node:vm')
const ts = require('typescript')

// Load the production client with an isolated fetch stub, without a test bundler.
const { outputText } = ts.transpileModule(
  readFileSync(resolve(__dirname, '../src/lib/api.ts'), 'utf8'),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } },
)

function createClient(response, { status = 200, reject = false } = {}) {
  const calls = []
  const context = {
    exports: {},
    process: { env: { NEXT_PUBLIC_API_URL: 'https://api.example.test' } },
    URLSearchParams,
    console: { error() {} },
    fetch: async (url, options) => {
      calls.push({ url, options })
      if (reject) throw new Error('Network unavailable')
      return { ok: status < 400, status, json: async () => response }
    },
  }
  vm.runInNewContext(outputText, context)
  return { api: context.exports.api, calls }
}

test('dashboard methods call real endpoints and preserve response envelopes', async () => {
  const response = { success: true, data: { total_records: 42, indicator_count: 2 } }
  const { api, calls } = createClient(response)
  assert.equal(await api.getStats(), response)
  assert.equal(await api.getCollectors(), response)
  assert.equal(await api.getTrendData('corn price/spot', 30), response)
  assert.equal(calls[0].url, 'https://api.example.test/api/data/stats')
  assert.equal(calls[1].url, 'https://api.example.test/api/collectors')
  const trendUrl = new URL(calls[2].url)
  assert.equal(trendUrl.pathname, '/api/data/trend')
  assert.equal(trendUrl.searchParams.get('indicator'), 'corn price/spot')
  assert.equal(trendUrl.searchParams.get('days'), '30')
  await api.getTrendData('corn_price')
  assert.equal(new URL(calls[3].url).searchParams.get('days'), '7')
})

test('adapter list and details preserve flattened fields and nullable sources', async () => {
  const adapter = { id: 'adapter-1', name: 'Collector', source: null }
  const { api, calls } = createClient({ success: true, data: [adapter] })
  const list = await api.listAdapters()
  assert.equal(list.data[0].id, 'adapter-1')
  assert.equal(list.data[0].name, 'Collector')
  assert.equal(list.data[0].source, null)
  assert.equal(list.data[0].adapter, undefined)
  const detailClient = createClient({ success: true, data: adapter })
  const detail = await detailClient.api.getAdapter('adapter-1')
  assert.equal(detail.data.name, 'Collector')
  assert.equal(calls[0].url, 'https://api.example.test/api/adapters')
  assert.equal(detailClient.calls[0].url, 'https://api.example.test/api/adapters/adapter-1')
})

test('record queries normalize Decimal strings, zero, null and invalid values', async () => {
  const { api, calls } = createClient({
    success: true,
    data: ['2450.25', 12.5, '0', 0, null, 'not-a-number', 'Infinity'].map((value, i) => ({ id: String(i), value })),
  })
  const response = await api.queryRecords({ adapter_id: 'adapter-1', limit: 50 })
  assert.deepEqual(Array.from(response.data, record => record.value), [2450.25, 12.5, 0, 0, null, null, null])
  assert.equal(response.data[0].value.toFixed(2), '2450.25')
  assert.equal(response.data[2].value.toFixed(2), '0.00')
  assert.equal(response.data[4].value, null)
  assert.equal(response.data[5].value, null)
  const url = new URL(calls[0].url)
  assert.equal(url.searchParams.get('adapter_id'), 'adapter-1')
  assert.equal(url.searchParams.get('limit'), '50')

  const records = await api.getAdapterRecords('adapter-1', 20)
  assert.equal(records.data[0].value.toFixed(2), '2450.25')
  assert.equal(calls[1].url, 'https://api.example.test/api/adapters/adapter-1/records?limit=20')
})

test('empty record sets and unsuccessful envelopes are preserved', async () => {
  const empty = await createClient({ success: true, data: [] }).api.queryRecords()
  assert.equal(empty.data.length, 0)
  for (const data of [null, undefined]) {
    const response = await createClient({ success: false, data, message: 'Query failed' }).api.queryRecords()
    assert.equal(response.success, false)
    assert.equal(response.data, data)
    assert.equal(response.message, 'Query failed')
  }
})

test('HTTP and network errors reject instead of returning mock data', async () => {
  await assert.rejects(createClient(null, { status: 500 }).api.getStats(), /status: 500/)
  await assert.rejects(createClient(null, { reject: true }).api.getCollectors(), /Network unavailable/)
})
