import React, { useState } from 'react'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { useToast } from '../ui/Toast'
import { Link } from 'react-router-dom'

export function Signup() {
  const { push } = useToast()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState({})

  const onSubmit = e => {
    e.preventDefault()
    const nextErrors = {}
    if (!email) nextErrors.email = 'Email is required'
    if (!password) nextErrors.password = 'Password is required'
    if (password !== confirm) nextErrors.confirm = 'Passwords do not match'
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length === 0) {
      push({ title: 'Account created', description: 'You can now log in' })
    }
  }

  return (
    <div className="max-w-md mx-auto">
      <h1 className="text-2xl font-bold">Sign up</h1>
      <form className="mt-6 space-y-4" onSubmit={onSubmit}>
        <Input id="email" label="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} error={errors.email} />
        <Input id="password" label="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} error={errors.password} />
        <Input id="confirm" label="Confirm Password" type="password" value={confirm} onChange={e => setConfirm(e.target.value)} error={errors.confirm} />
        <Button type="submit" className="w-full">Create account</Button>
      </form>
      <p className="mt-4 text-sm text-base-600">Already have an account? <Link to="/login" className="text-accent-600">Log in</Link></p>
    </div>
  )
}

export default Signup
