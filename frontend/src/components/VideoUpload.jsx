import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, RefreshCw } from 'lucide-react';
import { mockUpload, mockExportExcel, mockExportReport } from '../data';

export function VideoUpload() {
  const [file, setFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const fileInputRef = useRef();
  const navigate = useNavigate();

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.type.startsWith('video/')) {
      setFile(droppedFile);
      processVideo(droppedFile);
    }
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      processVideo(selectedFile);
    }
  };

  const processVideo = async (videoFile) => {
    setProcessing(true);
    setProgress(0);
    setResult(null);
    const interval = setInterval(() => setProgress(prev => Math.min(prev + 10, 90)), 300);
    try {
      const result = await mockUpload(videoFile); // Pass file to API
      setProgress(100);
      setResult(result);
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      clearInterval(interval);
      setProcessing(false);
    }
  };

  const handleExportAll = async () => {
    const blob = await mockExportExcel();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'events.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportReports = async () => {
    for (let i = 1; i <= 3; i++) {
      const blob = await mockExportReport(i);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Incident_${String(i).padStart(3, '0')}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div
        className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-600 mb-4">Drag and drop a video file here, or</p>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          accept="video/*"
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current.click()}
          className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700"
        >
          Select Video
        </button>
      </div>

      {processing && (
        <div className="mt-8">
          <p className="text-gray-600 mb-2">Processing video...</p>
          <div className="progress-bar">
            <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {result && (
        <div className="mt-8 bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold mb-4">Processing Complete</h2>
          <p className="text-gray-600 mb-4">{result.eventsDetected} disposal events detected</p>
          
          <div className="space-y-4">
            <button
              onClick={handleExportAll}
              className="w-full bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 flex items-center justify-center"
            >
              <FileText className="h-5 w-5 mr-2" />
              Export All Events as Excel
            </button>
            
            <button
              onClick={handleExportReports}
              className="w-full bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 flex items-center justify-center"
            >
              <FileText className="h-5 w-5 mr-2" />
              Export Individual Reports
            </button>
            
            <button
              onClick={() => navigate('/events')}
              className="w-full border border-indigo-600 text-indigo-600 px-4 py-2 rounded-md hover:bg-indigo-50"
            >
              View Events
            </button>
            
            <button
              onClick={() => {
                setFile(null);
                setResult(null);
                setProgress(0);
              }}
              className="w-full border border-gray-300 text-gray-600 px-4 py-2 rounded-md hover:bg-gray-50 flex items-center justify-center"
            >
              <RefreshCw className="h-5 w-5 mr-2" />
              Reprocess
            </button>
          </div>
        </div>
      )}
    </div>
  );
}