import React, { useState } from 'react'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { useToast } from '../ui/Toast'
import { Link } from 'react-router-dom'

export function ForgotPassword() {
  const { push } = useToast()
  const [email, setEmail] = useState('')
  const [errors, setErrors] = useState({})

  const onSubmit = e => {
    e.preventDefault()
    const nextErrors = {}
    if (!email) nextErrors.email = 'Email is required'
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length === 0) {
      push({ title: 'Reset link sent', description: 'Check your inbox' })
    }
  }

  return (
    <div className="max-w-md mx-auto">
      <h1 className="text-2xl font-bold">Forgot password</h1>
      <form className="mt-6 space-y-4" onSubmit={onSubmit}>
        <Input id="email" label="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} error={errors.email} />
        <Button type="submit" className="w-full">Send reset link</Button>
      </form>
      <p className="mt-4 text-sm text-base-600"><Link to="/login" className="text-accent-600">Back to login</Link></p>
    </div>
  )
}

export default ForgotPassword
