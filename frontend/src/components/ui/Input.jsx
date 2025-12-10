import React from 'react'

export function Input({ label, hint, error, className = '', ...props }) {
  return (
    <div className={`space-y-1 ${className}`}>
      {label && <label className="text-sm font-medium text-base-700">{label}</label>}
      <input
        className={`w-full h-10 px-3 rounded-lg border focus:ring-2 focus:ring-accent-500 focus:border-accent-500 placeholder-base-400 ${error ? 'border-danger' : 'border-base-300'}`}
        aria-invalid={!!error}
        aria-describedby={hint ? `${props.id}-hint` : undefined}
        {...props}
      />
      {hint && !error && <p id={`${props.id}-hint`} className="text-xs text-base-500">{hint}</p>}
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  )
}

export default Input
