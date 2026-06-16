import sqlite3
import os
import utils

class DataBaseOperate:
    def __init__(self, path: str, points: int = 300):
        os.makedirs(path, exist_ok=True)

        self.db_path = os.path.join(path, "DataBase.db")
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.points = points

        self.cursor.execute(
            """
               CREATE TABLE IF NOT EXISTS samples
               (
                    id TEXT PRIMARY KEY,
                    sample_path TEXT NOT NULL,
                    size REAL,
                    height REAL
               );
            """
        )
        self.point_columns = ",\n".join(
            f"p{i:03d} INTEGER" for i in range(points)
        )
        self.point_names = ",\n".join(
            f"p{i:03d}" for i in range(points)
        )
        self.cursor.execute(
            f"""
                CREATE TABLE IF NOT EXISTS responses 
                (
                    id TEXT,
                    direct INTEGER,
                    angle REAL,
                    {self.point_columns},
                    PRIMARY KEY (id, direct, angle),
                    FOREIGN KEY (id) REFERENCES samples(id)
                );
            """
        )

        self.point_columns_angle = ",\n".join(
            f"p{i:03d} REAL" for i in range(points)
        )
        self.cursor.execute(
            f"""
                        CREATE TABLE IF NOT EXISTS responses_angle 
                        (
                            id TEXT,
                            direct INTEGER,
                            angle REAL,
                            {self.point_columns_angle},
                            PRIMARY KEY (id, direct, angle),
                            FOREIGN KEY (id) REFERENCES samples(id)
                        );
                    """
        )


    def insert_sample(self, sample_id: str, sample_path: str, size: float, height: float):
        self.cursor.execute(
            """
                INSERT OR IGNORE INTO samples (id, sample_path, size, height)
                VALUES (?, ?, ?, ?)
            """,
            (sample_id, sample_path, size, height)
        )

    def insert_response(self, sample_id: str, angle: float, direct: int, Sparameters: list, Phase: list):
        Sparameters = [int(x) for x in Sparameters]
        Phase = [float(x) for x in Phase]
        placeholders = ", ".join("?" for _ in range(self.points))
        self.cursor.execute(
            f"""
                INSERT OR REPLACE INTO responses
                (id, direct, angle, {self.point_names})
                VALUES (?, ?, ?, {placeholders})
            """,
            (sample_id, direct, angle, *Sparameters)
        )
        self.cursor.execute(
            f"""
                        INSERT OR REPLACE INTO responses_angle
                        (id, direct, angle, {self.point_names})
                        VALUES (?, ?, ?, {placeholders})
                    """,
            (sample_id, direct, angle, *Phase)
        )


    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.commit()
        self.conn.close()
