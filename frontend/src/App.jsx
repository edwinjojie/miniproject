import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Home } from './components/Home';
import { VideoUpload } from './components/VideoUpload';
import { CameraDashboard } from './components/CameraDashboard';
import { EventReview } from './components/EventReview';
import { About } from './components/About';
import { Camera, Upload, Monitor, FileText, Info } from 'lucide-react';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-lg">
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex justify-between h-16">
              <div className="flex space-x-8">
               <span>Clean AI</span>
              </div>
              <div className="flex space-x-8">
                <Link to="/" className="flex items-center space-x-2 text-gray-900 hover:text-indigo-600">
                  <Camera className="h-5 w-5" />
                  <span>Home</span>
                </Link>
                <Link to="/upload" className="flex items-center space-x-2 text-gray-900 hover:text-indigo-600">
                  <Upload className="h-5 w-5" />
                  <span>Upload</span>
                </Link>
                <Link to="/dashboard" className="flex items-center space-x-2 text-gray-900 hover:text-indigo-600">
                  <Monitor className="h-5 w-5" />
                  <span>Dashboard</span>
                </Link>
                <Link to="/events" className="flex items-center space-x-2 text-gray-900 hover:text-indigo-600">
                  <FileText className="h-5 w-5" />
                  <span>Events</span>
                </Link>
                <Link to="/about" className="flex items-center space-x-2 text-gray-900 hover:text-indigo-600">
                  <Info className="h-5 w-5" />
                  <span>About</span>
                </Link>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto py-6 px-4">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/upload" element={<VideoUpload />} />
            <Route path="/dashboard" element={<CameraDashboard />} />
            <Route path="/events" element={<EventReview />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;