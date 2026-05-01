from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass
class Confidence:
    interval: float
    level: float

    def str_representation(self) -> str:
        return '±{:.4e} at {:.2%}'.format(self.interval, self.level)

    def __str__(self):
        return self.str_representation()


class Datapoint(ABC):
    @abstractmethod
    def to_point(self, unit: str) -> dict[str, Any]:
        pass

    def format_for_table_name(physical_unit: str, parameter: str) -> str:
        return f'{physical_unit}_{parameter}'.lower()

class Measurement(Datapoint):
    def __init__(
        self,
        parameter: str,
        value: Any,
        units: str,
        confidence: None | Confidence = None,
        time: None | datetime = None
    ):
        self.parameter = parameter
        self.value = value
        self.units = units
        self.confidence = confidence
        if time is None:
            time = datetime.now()
        self.time = time

    def to_point(self, unit: str):
        return {
            "measurement": Datapoint.format_for_table_name(unit, self.parameter),
            "tags": {
                "physical_unit": unit,
                "parameter": self.parameter
            },
            "fields": {
                "value": self.value,
                "confidence": str(self.confidence),
                "units": self.units
            },
            "time": self.time
        }

class WateringEvent(Datapoint):
    def __init__(
        self,
        dosage: int,
        time: datetime = datetime.now()
    ):
        self.dosage = dosage
        self.time = time

    def to_point(self, unit: str):
        return {
            "measurement": Datapoint.format_for_table_name(unit, "watering"),
            "tags": {"physical_unit": unit},
            "fields": {
                "value": self.dosage,
                "units": "ml"
            },
            "time": self.time
        }
    
