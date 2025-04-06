// API_BASE_URL is injected by Create React App from .env during build
// Fallback to localhost if not defined (safe for browser runtime)
const API_BASE_URL = typeof process !== 'undefined' && process.env ? process.env.REACT_APP_API_URL : 'http://localhost:5000';
let socket;

export const initializeWebSocket = (sid) => {
  socket = new WebSocket(`ws://${API_BASE_URL.replace('http', 'ws')}/socket.io/?EIO=4&transport=websocket&sid=${sid}`);
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.frame_update) {
      document.getElementById('live-canvas').src = `data:image/jpeg;base64,${data.frame_update.image}`;
    } else if (data.event_update) {
      window.dispatchEvent(new CustomEvent('newEvent', { detail: data.event_update.events }));
    } else if (data.processing_complete) {
      window.dispatchEvent(new CustomEvent('processingComplete', { detail: data.processing_complete }));
    }
  };
  socket.onerror = (error) => console.error('WebSocket error:', error);
  socket.onclose = () => console.log('WebSocket closed');
};

export const mockUpload = (file) => {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData,
    })
      .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
      })
      .then(data => {
        initializeWebSocket(data.sid); // Start WebSocket with session ID
        resolve(data);
      })
      .catch(error => reject(error));
  });
};

export const mockEvents = () => {
  return fetch(`${API_BASE_URL}/api/events`)
    .then(response => {
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return response.json();
    })
    .then(data => data)
    .catch(error => { throw error; });
};

export const mockExportExcel = (ids) => {
  const url = ids ? `${API_BASE_URL}/api/export/excel?ids=${ids.join(',')}` : `${API_BASE_URL}/api/export/excel`;
  return fetch(url)
    .then(response => {
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return response.blob();
    })
    .then(blob => blob)
    .catch(error => { throw error; });
};

export const mockExportReport = (id) => {
  return fetch(`${API_BASE_URL}/api/export/report/${id}`)
    .then(response => {
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return response.blob();
    })
    .then(blob => blob)
    .catch(error => { throw error; });
};

export const dummyEvents = [
  { id: 1, timestamp: '2025-03-26 14:32', source: 'Camera 01', type: 'Vehicle', description: 'Trash disposed', position: [320, 240, 1500] },
  { id: 2, timestamp: '2025-03-26 14:35', source: 'Uploaded Video', type: 'Human', description: 'Trash disposed', position: [400, 300, 1200] },
  { id: 3, timestamp: '2025-03-26 14:40', source: 'Camera 02', type: 'Vehicle', description: 'Trash disposed', position: [500, 350, 1800] }
];

export const dummyCameras = [
  { id: 1, name: 'Camera 01', path: 'riverside.mp4', status: 'Monitoring' },
  { id: 2, name: 'Camera 02', path: 'roadside.mp4', status: 'Monitoring' },
  { id: 3, name: 'Camera 03', path: 'test.mp4', status: 'Monitoring' }
];