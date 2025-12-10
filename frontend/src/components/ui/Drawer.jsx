import React from 'react'

export function Drawer({ open, side = 'right', onClose, children }) {
  if (!open) return null
  const pos = side === 'left' ? 'left-0' : 'right-0'
  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className={`absolute top-0 ${pos} h-full w-full max-w-md bg-white shadow-card`}>{children}</div>
    </div>
  )
}

export default Drawer
