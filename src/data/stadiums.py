from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = [
    "Stadium",
    "Country",
    "Location",
    "Capacity",
    "Opened",
    "Info",
    "Image_Filename",
]


@dataclass(frozen=True)
class Stadium:
    name: str
    country: str
    location: str
    capacity: int
    opened: int
    info: str
    image_filename: str


class StadiumRepository:
    """Loads and validates FIFA 2026 stadium detail records from a CSV file."""

    def __init__(self, csv_path: str | Path) -> None:
        self._csv_path = Path(csv_path)

    def load(self) -> list[Stadium]:
        df = pd.read_csv(self._csv_path)

        missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing expected columns: {missing}")

        stadiums: list[Stadium] = []
        for _, row in df.iterrows():
            try:
                capacity = int(row["Capacity"])
                opened = int(row["Opened"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Non-numeric value in row: {row.to_dict()}") from exc

            stadiums.append(
                Stadium(
                    name=_require_str(row["Stadium"], "Stadium"),
                    country=_require_str(row["Country"], "Country"),
                    location=_require_str(row["Location"], "Location"),
                    capacity=capacity,
                    opened=opened,
                    info=_require_str(row["Info"], "Info"),
                    image_filename=_require_str(row["Image_Filename"], "Image_Filename"),
                )
            )
        return stadiums


def _require_str(value: object, column: str) -> str:
    if pd.isna(value) or not str(value).strip():
        raise ValueError(f"Missing {column} in row")
    return str(value)
