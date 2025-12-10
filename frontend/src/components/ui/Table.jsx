import React, { useMemo, useState } from 'react'

export function Table({ columns, data, initialSort, pageSize = 10 }) {
  const [sort, setSort] = useState(initialSort || { key: columns[0]?.accessor, dir: 'asc' })
  const [page, setPage] = useState(0)
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    if (!query) return data
    const q = query.toLowerCase()
    return data.filter(row => Object.values(row).some(v => String(v).toLowerCase().includes(q)))
  }, [data, query])

  const sorted = useMemo(() => {
    if (!sort?.key) return filtered
    const dir = sort.dir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => (a[sort.key] > b[sort.key] ? dir : -dir))
  }, [filtered, sort])

  const pages = Math.ceil(sorted.length / pageSize)
  const pageData = sorted.slice(page * pageSize, page * pageSize + pageSize)

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <input
          value={query}
          onChange={e => { setQuery(e.target.value); setPage(0) }}
          placeholder="Search"
          className="h-10 px-3 w-64 rounded-lg border border-base-300 focus:ring-2 focus:ring-accent-500"
        />
        <div className="text-sm text-base-500">{filtered.length} results</div>
      </div>
      <div className="bg-white rounded-xl border border-base-200 shadow-soft overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-base-50">
            <tr>
              {columns.map(col => (
                <th key={col.accessor} className="px-6 py-3 text-left text-xs font-medium text-base-500 uppercase tracking-wider">
                  <button className="flex items-center gap-1" onClick={() => setSort(s => ({ key: col.accessor, dir: s.dir === 'asc' && s.key === col.accessor ? 'desc' : 'asc' }))}>
                    <span>{col.header}</span>
                    {sort.key === col.accessor && <span>{sort.dir === 'asc' ? '▲' : '▼'}</span>}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-base-200">
            {pageData.map((row, i) => (
              <tr key={i} className="hover:bg-base-50">
                {columns.map(col => (
                  <td key={col.accessor} className="px-6 py-4 text-sm text-base-700">
                    {col.cell ? col.cell(row[col.accessor], row) : row[col.accessor]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between">
        <div className="text-sm text-base-500">Page {page + 1} of {pages || 1}</div>
        <div className="flex items-center gap-2">
          <button className="px-3 py-2 rounded-lg border border-base-300" onClick={() => setPage(p => Math.max(p - 1, 0))} disabled={page === 0}>Prev</button>
          <button className="px-3 py-2 rounded-lg border border-base-300" onClick={() => setPage(p => Math.min(p + 1, pages - 1))} disabled={page >= pages - 1}>Next</button>
        </div>
      </div>
    </div>
  )
}

export default Table
