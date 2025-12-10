import React from 'react'

const variants = {
  primary: 'bg-accent-600 text-white hover:bg-accent-700 shadow-soft',
  secondary: 'bg-base-100 text-base-900 hover:bg-base-200 border border-base-300',
  ghost: 'bg-transparent text-base-900 hover:bg-base-100'
}

const sizes = {
  sm: 'h-9 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
  lg: 'h-12 px-6 text-base'
}

export function Button({ variant = 'primary', size = 'md', className = '', children, ...props }) {
  const base = 'inline-flex items-center justify-center rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-accent-500 disabled:opacity-50 disabled:cursor-not-allowed'
  return (
    <button className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...props}>
      {children}
    </button>
  )
}

export default Button
