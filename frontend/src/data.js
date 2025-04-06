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

export const mockUpload = (file) => {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    fetch('http://localhost:5000/api/upload', {
      method: 'POST',
      body: formData,
    })
      .then(response => response.json())
      .then(data => resolve(data))
      .catch(error => reject(error));
  });
};

export const mockEvents = () => {
  return fetch('http://localhost:5000/api/events')
    .then(response => response.json())
    .then(data => data);
};

export const mockExportExcel = (ids) => {
  const url = ids ? `http://localhost:5000/api/export/excel?ids=${ids.join(',')}` : 'http://localhost:5000/api/export/excel';
  return fetch(url)
    .then(response => response.blob())
    .then(blob => blob);
};

export const mockExportReport = (id) => {
  return fetch(`http://localhost:5000/api/export/report/${id}`)
    .then(response => response.blob())
    .then(blob => blob);
};