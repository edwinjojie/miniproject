import React, { useState, useRef, useEffect } from 'react'

export function Dropdown({ trigger, children }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  useEffect(() => {
    const onClick = e => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])
  return (
    <div className="relative" ref={ref}>
      <div onClick={() => setOpen(v => !v)} aria-haspopup="menu" aria-expanded={open}>
        {trigger}
      </div>
      {open && (
        <div role="menu" className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-card border border-base-200 p-2">
          {children}
        </div>
      )}
    </div>
  )
}

export function DropdownItem({ children, onClick }) {
  return (
    <button onClick={onClick} role="menuitem" className="w-full text-left px-3 py-2 rounded-lg hover:bg-base-100">
      {children}
    </button>
  )
}

export default Dropdown
