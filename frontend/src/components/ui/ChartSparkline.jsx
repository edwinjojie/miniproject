import React from 'react'

export function ChartSparkline({ data = [], width = 180, height = 48, color = '#6366f1' }) {
  if (!data.length) data = [0, 5, 2, 8, 4, 9, 6]
  const max = Math.max(...data)
  const points = data.map((d, i) => `${(i/(data.length-1))*width},${height - (d/max)*height}`).join(' ')
  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" />
      {data.map((d, i) => (
        <circle key={i} cx={(i/(data.length-1))*width} cy={height - (d/max)*height} r="2" fill={color} />
      ))}
    </svg>
  )
}

export default ChartSparkline
