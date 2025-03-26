# spatial_temporal_data.py

import json
import sqlite3
from collections import defaultdict
import logging
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SpatialTemporalData:
    def __init__(self, frame_data_path="./data/frame_data.json", output_db_path="./data/spatial_temporal.db"):
        """
        Initialize SpatialTemporalData module.

        Args:
            frame_data_path (str): Path to JSON from Module 1.
            output_db_path (str): Path for SQLite database.
        """
        self.frame_data_path = frame_data_path
        self.output_db_path = output_db_path
        self.tracks = defaultdict(list)  # {obj_id: [{'frame_id': int, 'position': (x, y), 'type': str}]}

    def load_frame_data(self):
        """Load frame data from JSON."""
        try:
            with open(self.frame_data_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load frame data: {e}")
            raise

    def organize_data(self, frame_data):
        """Organize detections into tracks."""
        for frame in frame_data:
            for det in frame['detections']:
                if det['id'] is not None:
                    self.tracks[det['id']].append({
                        'frame_id': frame['frame_id'],
                        'position': det['position'],
                        'type': det['type']
                    })

    def interpolate_missing_positions(self, max_gap=5):
        """Interpolate positions for small gaps in tracks."""
        for obj_id, positions in self.tracks.items():
            positions.sort(key=lambda x: x['frame_id'])
            interpolated = []
            for i in range(len(positions) - 1):
                curr, next_pos = positions[i], positions[i + 1]
                frame_diff = next_pos['frame_id'] - curr['frame_id']
                interpolated.append(curr)
                if 1 < frame_diff <= max_gap:
                    for f in range(curr['frame_id'] + 1, next_pos['frame_id']):
                        alpha = (f - curr['frame_id']) / frame_diff
                        pos = (
                            int(curr['position'][0] + alpha * (next_pos['position'][0] - curr['position'][0])),
                            int(curr['position'][1] + alpha * (next_pos['position'][1] - curr['position'][1]))
                        )
                        interpolated.append({'frame_id': f, 'position': pos, 'type': curr['type']})
            interpolated.append(positions[-1])
            self.tracks[obj_id] = interpolated

    def save_to_database(self):
        """Save tracks to SQLite database."""
        conn = sqlite3.connect(self.output_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracks (
                object_id INTEGER,
                frame_id INTEGER,
                x INTEGER,
                y INTEGER,
                type TEXT
            )
        ''')
        for obj_id, positions in self.tracks.items():
            for pos in positions:
                cursor.execute('INSERT INTO tracks VALUES (?, ?, ?, ?, ?)',
                               (obj_id, pos['frame_id'], pos['position'][0], pos['position'][1], pos['type']))
        conn.commit()
        conn.close()
        logger.info(f"Saved tracks to {self.output_db_path}")

    def get_track(self, obj_id):
        """Retrieve a track by object ID."""
        return self.tracks.get(obj_id, [])

    def get_positions_at_frame(self, frame_id):
        """Retrieve positions at a specific frame."""
        return [
            {'object_id': obj_id, 'type': pos['type'], 'position': pos['position']}
            for obj_id, track in self.tracks.items()
            for pos in track if pos['frame_id'] == frame_id
        ]

    def process(self):
        """Run full processing pipeline."""
        frame_data = self.load_frame_data()
        self.organize_data(frame_data)
        self.interpolate_missing_positions()
        self.save_to_database()

if __name__ == "__main__":
    st_data = SpatialTemporalData()
    st_data.process()
    print("Spatial-temporal data processed.")