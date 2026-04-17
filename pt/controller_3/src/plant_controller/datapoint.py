from dataclasses import dataclass

@dataclass
class Confidence:
    interval: float
    level: float

    def str_representation(self) -> str:
        return '±{:.4e} at {:.2%}'.format(self.interval, self.level)

    def __str__(self):
        return self.str_representation()

@dataclass
class Datapoint:
    parameter: str
    value: any
    confidence: None | Confidence
    units: str
