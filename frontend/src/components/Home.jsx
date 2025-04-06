import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Monitor, FileText } from 'lucide-react';

export function Home() {
  const navigate = useNavigate();

  return (
    <div className="max-w-4xl mx-auto text-center">
      <h1 className="text-4xl font-bold text-gray-900 mb-8">
        Trash Disposal Detection System - Test and Monitor
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <button
          onClick={() => navigate('/upload')}
          className="flex flex-col items-center p-6 bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow"
        >
          <Upload className="h-12 w-12 text-indigo-600 mb-4" />
          <span className="text-lg font-medium">Upload Video</span>
        </button>

        <button
          onClick={() => navigate('/dashboard')}
          className="flex flex-col items-center p-6 bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow"
        >
          <Monitor className="h-12 w-12 text-indigo-600 mb-4" />
          <span className="text-lg font-medium">Camera Dashboard</span>
        </button>

        <button
          onClick={() => navigate('/events')}
          className="flex flex-col items-center p-6 bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow"
        >
          <FileText className="h-12 w-12 text-indigo-600 mb-4" />
          <span className="text-lg font-medium">View Events</span>
        </button>
      </div>

      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold mb-4">System Status</h2>
        <p className="text-gray-600">Last processed video: test_video.mp4</p>
        <p className="text-gray-600">Active cameras: 3</p>
        <p className="text-gray-600">Events today: 15</p>
      </div>
    </div>
  );
}