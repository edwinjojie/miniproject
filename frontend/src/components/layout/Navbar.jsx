import React from 'react'
import { Link } from 'react-router-dom'
import { Dropdown, DropdownItem } from '../ui/Dropdown'

export function Navbar() {
  return (
    <nav className="sticky top-0 z-40 bg-white/80 backdrop-blur border-b border-base-200">
      <div className="max-w-7xl mx-auto px-4">
        <div className="h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link to="/" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-accent-600" />
              <span className="font-semibold">CleanAI</span>
            </Link>
            <div className="hidden md:flex items-center gap-6">
              <Link to="/" className="text-base-700 hover:text-base-900">Home</Link>
              <Link to="/upload" className="text-base-700 hover:text-base-900">Upload</Link>
              <Link to="/dashboard" className="text-base-700 hover:text-base-900">Dashboard</Link>
              <Link to="/events" className="text-base-700 hover:text-base-900">Events</Link>
              <Link to="/about" className="text-base-700 hover:text-base-900">About</Link>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Dropdown
              trigger={
                <button className="h-10 w-10 rounded-full bg-base-200" aria-label="Profile" />
              }
            >
              <div className="px-3 py-2">
                <div className="font-medium">User</div>
                <div className="text-sm text-base-500">user@example.com</div>
              </div>
              <DropdownItem>
                <Link to="/settings">Settings</Link>
              </DropdownItem>
              <DropdownItem>Logout</DropdownItem>
            </Dropdown>
          </div>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
