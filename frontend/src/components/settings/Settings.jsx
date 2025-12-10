import React, { useState } from 'react'
import { Card } from '../ui/Card'
import { Input } from '../ui/Input'
import { Button } from '../ui/Button'
import { useToast } from '../ui/Toast'

export function Settings() {
  const { push } = useToast()
  const [name, setName] = useState('Jane Doe')
  const [email, setEmail] = useState('user@example.com')
  const [org, setOrg] = useState('CleanAI')

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Card title="Profile" subtitle="Manage account details">
        <div className="space-y-4">
          <Input id="name" label="Name" value={name} onChange={e => setName(e.target.value)} />
          <Input id="email" label="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} />
          <Input id="org" label="Organization" value={org} onChange={e => setOrg(e.target.value)} />
          <div className="flex justify-end">
            <Button onClick={() => push({ title: 'Profile saved' })}>Save changes</Button>
          </div>
        </div>
      </Card>
      <Card title="Preferences" subtitle="Interface and notifications">
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="rounded" defaultChecked />
            Enable email notifications
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="rounded" />
            Reduce motion
          </label>
          <div className="flex justify-end">
            <Button variant="secondary" onClick={() => push({ title: 'Preferences updated' })}>Update</Button>
          </div>
        </div>
      </Card>
    </div>
  )
}

export default Settings
