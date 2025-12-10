import React from 'react'

export function ChartBar({ data = [], width = 240, height = 120, color = '#6366f1' }) {
  if (!data.length) data = [5, 8, 3, 7, 4]
  const max = Math.max(...data)
  const barWidth = width / data.length - 8
  return (
    <svg width={width} height={height}>
      {data.map((d, i) => {
        const h = (d / max) * (height - 16)
        const x = i * (barWidth + 8)
        const y = height - h
        return <rect key={i} x={x} y={y} width={barWidth} height={h} rx="6" fill={color} />
      })}
    </svg>
  )
}

export default ChartBar
