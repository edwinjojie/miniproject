import React, { useState } from 'react';
import { Play, Pause, RefreshCw, Download } from 'lucide-react';
import { dummyCameras, mockExportExcel, mockExportReport } from '../data';

export function CameraDashboard() {
  const [cameras, setCameras] = useState(dummyCameras);
  const [selectedEvents, setSelectedEvents] = useState({});

  const handlePlayPause = (id) => {
    console.log(`${cameras.find(c => c.id === id).status === 'Playing' ? 'Paused' : 'Playing'} camera ${id}`);
    setCameras(cameras.map(cam =>
      cam.id === id
        ? { ...cam, status: cam.status === 'Playing' ? 'Monitoring' : 'Playing' }
        : cam
    ));
  };

  const handleSliderChange = (id, value) => {
    console.log(`Camera ${id} position: ${value}`);
  };

  const handlePathChange = (id, newPath) => {
    setCameras(cameras.map(cam =>
      cam.id === id ? { ...cam, path: newPath } : cam
    ));
  };

  const handleRefreshAll = () => {
    console.log('Refreshed all feeds');
  };

  const handleExtractIncidents = async (id) => {
    // Simulated incidents
    const incidents = [
      { id: `${id}-1`, timestamp: '00:32', description: 'Vehicle disposed trash' },
      { id: `${id}-2`, timestamp: '01:15', description: 'Person disposed trash' }
    ];
    return new Promise(resolve => setTimeout(() => resolve(incidents), 2000));
  };

  const handleExportSelected = async () => {
    const selectedIds = Object.entries(selectedEvents)
      .filter(([_, selected]) => selected)
      .map(([id]) => parseInt(id));
    
    const blob = await mockExportExcel(selectedIds);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'selected_events.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Camera Dashboard</h1>
        <button
          onClick={handleRefreshAll}
          className="flex items-center px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        >
          <RefreshCw className="h-5 w-5 mr-2" />
          Refresh All Feeds
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {cameras.map((camera) => (
          <div key={camera.id} className="bg-white rounded-lg shadow-md overflow-hidden">
            <div className="camera-feed">
              <img
                src={`https://source.unsplash.com/800x450/?security-camera&${camera.id}`}
                alt={camera.name}
                className="w-full h-full object-cover"
              />
              <div className="camera-controls">
                <button
                  onClick={() => handlePlayPause(camera.id)}
                  className="p-1 hover:text-indigo-400"
                >
                  {camera.status === 'Playing' ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
                </button>
                <input
                  type="range"
                  min="0"
                  max="100"
                  className="w-full mt-2"
                  onChange={(e) => handleSliderChange(camera.id, e.target.value)}
                />
              </div>
            </div>

            <div className="p-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">{camera.name}</h3>
                <span className="text-sm text-gray-500">{camera.status}</span>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Camera Path</label>
                  <input
                    type="text"
                    value={camera.path}
                    onChange={(e) => handlePathChange(camera.id, e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
                  />
                </div>

                <button
                  onClick={() => handleExtractIncidents(camera.id)}
                  className="w-full bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 flex items-center justify-center"
                >
                  <Download className="h-5 w-5 mr-2" />
                  Extract Incidents
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="fixed bottom-4 right-4">
        <button
          onClick={handleExportSelected}
          className="bg-indigo-600 text-white px-6 py-3 rounded-full shadow-lg hover:bg-indigo-700 flex items-center"
        >
          <Download className="h-5 w-5 mr-2" />
          Export Selected Events
        </button>
      </div>
    </div>
  );
}