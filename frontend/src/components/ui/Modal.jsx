import React from 'react'

export function Modal({ open, title, children, onClose, actions }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div className="w-full max-w-lg bg-white rounded-xl shadow-card">
          <div className="px-6 py-4 border-b border-base-200 flex items-center justify-between">
            <h3 className="text-base font-semibold text-base-900">{title}</h3>
            <button onClick={onClose} className="text-base-500 hover:text-base-700">×</button>
          </div>
          <div className="p-6">{children}</div>
          {actions && <div className="px-6 py-4 border-t border-base-200 flex justify-end gap-2">{actions}</div>}
        </div>
      </div>
    </div>
  )
}

export default Modal
