import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Home } from './components/Home';
import { VideoUpload } from './components/VideoUpload';
import { CameraDashboard } from './components/CameraDashboard';
import { EventReview } from './components/EventReview';
import { About } from './components/About';
import { Navbar } from './components/layout/Navbar';
import { Toaster } from './components/ui/Toast';
import { Login } from './components/auth/Login';
import { Signup } from './components/auth/Signup';
import { ForgotPassword } from './components/auth/ForgotPassword';
import { Settings } from './components/settings/Settings';

function App() {
  return (
    <Router>
      <Toaster>
        <div className="min-h-screen bg-gray-50">
          <Navbar />
          <main className="max-w-7xl mx-auto py-8 px-4">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/upload" element={<VideoUpload />} />
              <Route path="/dashboard" element={<CameraDashboard />} />
              <Route path="/events" element={<EventReview />} />
              <Route path="/about" element={<About />} />
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
              <Route path="/forgot" element={<ForgotPassword />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </Toaster>
    </Router>
  );
}

export default App;
