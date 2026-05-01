from collections.abc import Coroutine
from typing import Any

import adafruit_as7341

from . import Sensor
from ..datapoint import Datapoint, Confidence, Measurement
from ..com_bus import BlinkaI2CBus, I2CInterface

class LightConfidence(Confidence):
    def __init__(
        self,
        center_wavelenght_variance: int,
        full_width_half_maximum: int
    ):
        self.center_wavelength_variance = center_wavelenght_variance
        self.full_width_half_maximum = full_width_half_maximum

    def str_representation(self) -> str:
        return f"Center wavelength ±{self.center_wavelength_variance}nm, FWHM ±{self.full_width_half_maximum}nm"

class GreenhouseAS7341(Sensor, I2CInterface):
    def __init__(
        self,
        bus: BlinkaI2CBus,
        db_save_function: Coroutine[Any, Datapoint | list[Datapoint]],
        **kwargs: Any
    ):
        self.wrapped_sensor = adafruit_as7341.AS7341(bus.wrapped_bus)
        self.wrapped_sensor.gain = adafruit_as7341.Gain.GAIN_64X
        self.db_save_function = db_save_function
        self.time_between_reads = 15
        self.integration_time = (
            (self.wrapped_sensor.atime + 1)
            * (self.wrapped_sensor.astep + 1)
            * 2.78e-6
        )

    def phtoton_count_to_flux(self, count):
        return count / self.integration_time

    async def read(self):
        await self.db_save_function(
            [
                Measurement(
                    parameter="415nm",
                    value=self.phtoton_count_to_flux(
                        self.wrapped_sensor.channel_415nm
                    ),
                    confidence=LightConfidence(
                        center_wavelenght_variance=10,
                        full_width_half_maximum=26
                    ),
                    units="photons/s"
                ),
                Measurement(
                    parameter="445nm",
                    value=self.phtoton_count_to_flux(
                        self.wrapped_sensor.channel_445nm
                    ),
                    confidence=LightConfidence(
                        center_wavelenght_variance=10,
                        full_width_half_maximum=30
                    ),
                    units="photons/s"
                ),
                Measurement(
                    parameter="480nm",
                    value=self.phtoton_count_to_flux(
                        self.wrapped_sensor.channel_480nm
                    ),
                    confidence=LightConfidence(
                        center_wavelenght_variance=10,
                        full_width_half_maximum=36
                    ),
                    units="photons/s"
                ),
                Measurement(
                    parameter="515nm",
                    value=self.phtoton_count_to_flux(
                        self.wrapped_sensor.channel_515nm
                    ),
                    confidence=LightConfidence(
                        center_wavelenght_variance=10,
                        full_width_half_maximum=39
                    ),
                    units="photons/s"
                ),
                Measurement(
                    parameter="555nm",
                    value=self.phtoton_count_to_flux(
                        self.wrapped_sensor.channel_555nm
                    ),
                    confidence=LightConfidence(
                        center_wavelenght_variance=10,
                        full_width_half_maximum=39
                    ),
                    units="photons/s"
                ),
                Measurement(
                    parameter="590nm",
                    value=self.phtoton_count_to_flux(
                        self.wrapped_sensor.channel_590nm
                    ),
                    confidence=LightConfidence(
                        center_wavelenght_variance=10,
                        full_width_half_maximum=40
                    ),
                    units="photons/s"
                ),
                Measurement(
                    parameter="630nm",
                    value=self.phtoton_count_to_flux(
                        self.wrapped_sensor.channel_630nm
                    ),
                    confidence=LightConfidence(
                        center_wavelenght_variance=10,
                        full_width_half_maximum=50
                    ),
                    units="photons/s"
                ),
                Measurement(
                    parameter="680nm",
                    value=self.phtoton_count_to_flux(
                        self.wrapped_sensor.channel_680nm
                    ),
                    confidence=LightConfidence(
                        center_wavelenght_variance=10,
                        full_width_half_maximum=52
                    ),
                    units="photons/s"
                ),
                Measurement(
                    parameter="infrared (910nm)",
                    value=self.phtoton_count_to_flux(
                        self.wrapped_sensor.channel_nir
                    ),
                    units="photons/s"
                )
            ]
        )

    def get_capabilities(self):
        return {
            "415nm": {
                "units": "photons/s",
                "time between reads": str(self.time_between_reads) + " seconds",
                "integration time": str(self.integration_time) + " seconds"
            },
            "445nm": {
                "units": "photons/s",
                "time between reads": str(self.time_between_reads) + " seconds",
                "integration time": str(self.integration_time) + " seconds"
            },
            "480nm": {
                "units": "photons/s",
                "time between reads": str(self.time_between_reads) + " seconds",
                "integration time": str(self.integration_time) + " seconds"
            },
            "515nm": {
                "units": "photons/s",
                "time between reads": str(self.time_between_reads) + " seconds",
                "integration time": str(self.integration_time) + " seconds"
            },
            "555nm": {
                "units": "photons/s",
                "time between reads": str(self.time_between_reads) + " seconds",
                "integration time": str(self.integration_time) + " seconds"
            },
            "590nm": {
                "units": "photons/s",
                "time between reads": str(self.time_between_reads) + " seconds",
                "integration time": str(self.integration_time) + " seconds"
            },
            "630nm": {
                "units": "photons/s",
                "time between reads": str(self.time_between_reads) + " seconds",
                "integration time": str(self.integration_time) + " seconds"
            },
            "680nm": {
                "units": "photons/s",
                "time between reads": str(self.time_between_reads) + " seconds",
                "integration time": str(self.integration_time) + " seconds"
            },
            "IR": {
                "units": "photons/s",
                "time between reads": str(self.time_between_reads) + " seconds",
                "integration time": str(self.integration_time) + " seconds"
            }
        }