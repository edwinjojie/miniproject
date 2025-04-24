import React, { useState, useEffect } from 'react';
import { Download, ChevronDown, ChevronUp } from 'lucide-react';
//import { mockEvents, mockExportExcel, mockExportReport } from '../data';
import axios from 'axios'

/*export function EventReview() {
  const [events, setEvents] = useState([]);
  const [expandedEvent, setExpandedEvent] = useState(null);
  const [selectedEvents, setSelectedEvents] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    try {
      const data = await mockEvents();
      setEvents(data);
    } catch (error) {
      console.error('Failed to load events:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExportAll = async () => {
    const blob = await mockExportExcel();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'all_events.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportSelected = async () => {
    const selectedIds = Object.entries(selectedEvents)
      .filter(([_, selected]) => selected)
      .map(([id]) => parseInt(id));
    
    for (const id of selectedIds) {
      const blob = await mockExportReport(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Event_${id}_Report.txt`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-600">Loading events...</div>
      </div>
    );
  }

  return (*/
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Event Review</h1>
        <div className="space-x-4">
          <button
            onClick={handleExportAll}
            className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700"
          >
            Export All as Excel
          </button>
          <button
            onClick={handleExportSelected}
            className="border border-indigo-600 text-indigo-600 px-4 py-2 rounded-md hover:bg-indigo-50"
            disabled={!Object.values(selectedEvents).some(Boolean)}
          >
            Export Selected Reports
          </button>
        </div>
      </div>

      <div className="bg-white shadow-md rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <input
                  type="checkbox"
                  onChange={(e) => {
                    const newSelected = {};
                    events.forEach(event => {
                      newSelected[event.id] = e.target.checked;
                    });
                    setSelectedEvents(newSelected);
                  }}
                  checked={
                    Object.keys(selectedEvents).length === events.length &&
                    Object.values(selectedEvents).every(Boolean)
                  }
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Event ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Timestamp
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Source
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {events.map((event) => (
              <React.Fragment key={event.id}>
                <tr className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <input
                      type="checkbox"
                      checked={selectedEvents[event.id] || false}
                      onChange={(e) => {
                        setSelectedEvents({
                          ...selectedEvents,
                          [event.id]: e.target.checked
                        });
                      }}
                      className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">{event.id}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{event.timestamp}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{event.source}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{event.type}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{event.description}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => setExpandedEvent(expandedEvent === event.id ? null : event.id)}
                      className="text-indigo-600 hover:text-indigo-900"
                    >
                      {expandedEvent === event.id ? (
                        <ChevronUp className="h-5 w-5" />
                      ) : (
                        <ChevronDown className="h-5 w-5" />
                      )}
                    </button>
                  </td>
                </tr>
                {expandedEvent === event.id && (
                  <tr>
                    <td colSpan="7" className="px-6 py-4 bg-gray-50">
                      <div className="space-y-4">
                        <div>
                          <h4 className="font-medium">Video Snippet</h4>
                          <div className="mt-2 bg-black text-white p-4 rounded">
                            Video snippet here
                          </div>
                        </div>
                        <div>
                          <h4 className="font-medium">Position Data</h4>
                          <p className="mt-2">
                            X: {event.position[0]}, Y: {event.position[1]}, Z: {event.position[2]}
                          </p>
                        </div>
                        <button
                          onClick={async () => {
                            const blob = await mockExportReport(event.id);
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `Event_${event.id}_Report.txt`;
                            a.click();
                            URL.revokeObjectURL(url);
                          }}
                          className="flex items-center text-indigo-600 hover:text-indigo-900"
                        >
                          <Download className="h-5 w-5 mr-2" />
                          Download Report
                        </button>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
 // );
//}