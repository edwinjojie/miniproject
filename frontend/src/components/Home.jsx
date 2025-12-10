import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, Monitor, FileText } from 'lucide-react'
import { Button } from './ui/Button'
import { Card } from './ui/Card'

export function Home() {
  const navigate = useNavigate();

  return (
    <div className="max-w-7xl mx-auto">
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-b from-white to-base-100 border border-base-200 p-8 md:p-12">
        <div className="max-w-3xl">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-base-900">Trash Disposal Detection System</h1>
          <p className="mt-4 text-base-600 text-lg">Detect, track, and report disposal events with enterprise-grade clarity and speed.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button onClick={() => navigate('/upload')} size="lg">Upload Video</Button>
            <Button variant="secondary" onClick={() => navigate('/dashboard')} size="lg">Open Dashboard</Button>
          </div>
        </div>
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-accent-100" />
      </section>

      <section className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card title="Upload" subtitle="Process recorded footage">
          <div className="flex items-center gap-3">
            <Upload className="h-6 w-6 text-accent-600" />
            <p className="text-sm text-base-600">Drag and drop videos to analyze events.</p>
          </div>
        </Card>
        <Card title="Dashboard" subtitle="Monitor live feeds">
          <div className="flex items-center gap-3">
            <Monitor className="h-6 w-6 text-accent-600" />
            <p className="text-sm text-base-600">Manage multiple cameras with synchronized tracking.</p>
          </div>
        </Card>
        <Card title="Events" subtitle="Review and export">
          <div className="flex items-center gap-3">
            <FileText className="h-6 w-6 text-accent-600" />
            <p className="text-sm text-base-600">Filter, sort, and export incident data.</p>
          </div>
        </Card>
      </section>

      <section className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card title="System Status">
          <div className="space-y-2 text-sm text-base-700">
            <div className="flex justify-between"><span>Last processed video</span><span className="font-medium">test_video.mp4</span></div>
            <div className="flex justify-between"><span>Active cameras</span><span className="font-medium">3</span></div>
            <div className="flex justify-between"><span>Events today</span><span className="font-medium">15</span></div>
          </div>
        </Card>
        <Card title="Quick Actions">
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => navigate('/events')} variant="secondary">View Events</Button>
            <Button onClick={() => navigate('/about')} variant="ghost">Learn More</Button>
          </div>
        </Card>
        <Card title="Compliance">
          <p className="text-sm text-base-600">Built with accessibility and privacy best practices.</p>
        </Card>
      </section>
    </div>
  )
}
