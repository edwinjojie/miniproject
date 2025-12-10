import React, { useState } from 'react'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { useToast } from '../ui/Toast'
import { Link } from 'react-router-dom'

export function Login() {
  const { push } = useToast()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState({})

  const onSubmit = e => {
    e.preventDefault()
    const nextErrors = {}
    if (!email) nextErrors.email = 'Email is required'
    if (!password) nextErrors.password = 'Password is required'
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length === 0) {
      push({ title: 'Logged in', description: 'Welcome back!' })
    }
  }

  return (
    <div className="max-w-md mx-auto">
      <h1 className="text-2xl font-bold">Log in</h1>
      <form className="mt-6 space-y-4" onSubmit={onSubmit}>
        <Input id="email" label="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} error={errors.email} />
        <Input id="password" label="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} error={errors.password} />
        <div className="flex items-center justify-between">
          <Link to="/forgot" className="text-sm text-accent-600">Forgot password?</Link>
        </div>
        <Button type="submit" className="w-full">Log in</Button>
      </form>
      <p className="mt-4 text-sm text-base-600">Don't have an account? <Link to="/signup" className="text-accent-600">Sign up</Link></p>
    </div>
  )
}

export default Login
