import React, { createContext, useContext, useState, useCallback } from 'react'

const ToastCtx = createContext({ push: () => {} })

export function Toaster({ children }) {
  const [items, setItems] = useState([])
  const push = useCallback(({ title, description, type = 'default' }) => {
    const id = Math.random().toString(36).slice(2)
    setItems(prev => [...prev, { id, title, description, type }])
    setTimeout(() => setItems(prev => prev.filter(i => i.id !== id)), 3000)
  }, [])
  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-4 right-4 space-y-2 z-50">
        {items.map(i => (
          <div key={i.id} className={`min-w-[240px] px-4 py-3 rounded-lg shadow-soft bg-white border ${i.type === 'error' ? 'border-danger' : 'border-base-200'}`}>
            <div className="font-medium">{i.title}</div>
            {i.description && <div className="text-sm text-base-500">{i.description}</div>}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

export function useToast() {
  return useContext(ToastCtx)
}

export default Toaster
