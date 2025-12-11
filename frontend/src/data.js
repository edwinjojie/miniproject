import { io } from 'socket.io-client'
const API_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL) ? import.meta.env.VITE_API_URL : 'http://localhost:5000';
let socket;
let sid;

export const connectSocket = () => {
  return new Promise(resolve => {
    socket = io(API_BASE_URL);
    socket.on('connect', () => {
      sid = socket.id;
      resolve(sid);
    });
    socket.on('frame_update', (data) => {
      const el = document.getElementById('live-canvas');
      if (el) el.src = `data:image/jpeg;base64,${data.image}`;
    });
    socket.on('processing_complete', (data) => {
      window.dispatchEvent(new CustomEvent('processingComplete', { detail: { eventsDetected: (data.events || []).length, ...data } }));
      if (Array.isArray(data.events) && data.events.length) {
        window.dispatchEvent(new CustomEvent('newEvent', { detail: data.events }));
      }
    });
  });
};

export const setVisualizationMode = (mode) => {
  const ready = socket && socket.connected ? Promise.resolve(sid) : connectSocket();
  ready.then(() => {
    socket.emit('set_visualization_mode', { mode });
  });
};

export const ensureSocket = () => {
  return socket && socket.connected ? Promise.resolve(sid) : connectSocket();
};

export const mockUpload = (file) => {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    const ensureSocket = socket && socket.connected ? Promise.resolve(sid) : connectSocket();
    ensureSocket.then(() => {
      if (sid) formData.append('sid', sid);
      fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData,
      })
      .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
      })
      .then(data => resolve(data))
      .catch(error => reject(error));
    });
  });
};

export const mockEvents = () => {
  return fetch(`${API_BASE_URL}/api/events`)
    .then(response => {
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return response.json();
    })
    .catch(() => {
      return dummyEvents;
    });
};

export const mockExportExcel = (ids) => {
  const url = ids ? `${API_BASE_URL}/api/export/excel?ids=${ids.join(',')}` : `${API_BASE_URL}/api/export/excel`;
  return fetch(url)
    .then(response => {
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return response.blob();
    })
    .catch(() => {
      const rows = [['Event ID','Timestamp','Source','Type','Description','X','Y','Z']];
      const source = ids && ids.length ? dummyEvents.filter(e => ids.includes(e.id)) : dummyEvents;
      source.forEach(e => rows.push([e.id, e.timestamp, e.source, e.type, e.description, e.position[0], e.position[1], e.position[2]]));
      const csv = rows.map(r => r.join(',')).join('\n');
      return new Blob([csv], { type: 'text/csv' });
    });
};

export const mockExportReport = (id) => {
  return fetch(`${API_BASE_URL}/api/export/report/${id}`)
    .then(response => {
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return response.blob();
    })
    .catch(() => {
      const e = dummyEvents.find(x => x.id === id) || dummyEvents[0];
      const content = `Event Report\nID: ${e.id}\nTimestamp: ${e.timestamp}\nSource: ${e.source}\nType: ${e.type}\nDescription: ${e.description}\nPosition: ${e.position.join(', ')}`;
      return new Blob([content], { type: 'text/plain' });
    });
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
