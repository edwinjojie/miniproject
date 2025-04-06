import React from 'react';
import { Mail, Github } from 'lucide-react';

export function About() {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white shadow-md rounded-lg overflow-hidden">
        <div className="px-6 py-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">
            Trash Disposal Detection System
          </h1>
          
          <div className="prose max-w-none">
            <p className="text-lg text-gray-600 mb-6">
              Our system uses advanced AI technology to detect and track disposal events in 3D space.
              By combining computer vision and spatial analysis, we can identify and document
              illegal dumping activities in real-time.
            </p>

            <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">
              Key Features
            </h2>
            
            <ul className="list-disc pl-6 text-gray-600 space-y-2">
              <li>Real-time video processing and analysis</li>
              <li>Multi-camera support with synchronized tracking</li>
              <li>3D position tracking of detected events</li>
              <li>Automated report generation and incident logging</li>
              <li>Export capabilities for data analysis</li>
            </ul>

            <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">
              Technical Details
            </h2>
            
            <p className="text-gray-600 mb-4">
              The system is built using a combination of modern technologies:
            </p>
            
            <ul className="list-disc pl-6 text-gray-600 space-y-2">
              <li>Frontend: React with modern JavaScript</li>
              <li>Backend: Python Flask (API endpoints)</li>
              <li>Computer Vision: OpenCV and custom AI models</li>
              <li>3D Analysis: Custom spatial-temporal algorithms</li>
            </ul>

            <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">
              Contact Information
            </h2>
            
            <div className="space-y-4">
              <div className="flex items-center space-x-2 text-gray-600">
                <Mail className="h-5 w-5" />
                <span>admin@test.com</span>
              </div>
              
              <div className="flex items-center space-x-2 text-gray-600">
                <Github className="h-5 w-5" />
                <span>github.com/trash-detection-system</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}