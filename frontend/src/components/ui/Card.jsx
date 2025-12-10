import React from 'react'

export function Card({ title, subtitle, actions, children, className = '' }) {
  return (
    <div className={`bg-white rounded-xl shadow-card ${className}`}>
      {(title || actions) && (
        <div className="px-6 py-4 border-b border-base-200 flex items-center justify-between">
          <div>
            {title && <h3 className="text-base font-semibold text-base-900">{title}</h3>}
            {subtitle && <p className="text-sm text-base-500">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      <div className="p-6">{children}</div>
    </div>
  )
}

export default Card
