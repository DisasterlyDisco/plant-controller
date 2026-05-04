import logging
logger = logging.getLogger(__name__)

from collections.abc import Coroutine
from time import sleep
from typing import Any

import anyio

from . import Pump
from ..datapoint import Datapoint, WateringEvent
from ..cli_helpers import clear_screen
from ..com_bus import MODBUS, MODBUSInterface
from ..setup_actions import HasSetupFunctionsMixin

class CS_IO404_Based_AD20P_1230E(Pump, MODBUSInterface, HasSetupFunctionsMixin):
    def __init__(
        self,
        bus: MODBUS,
        db_save_function: Coroutine[Any, Datapoint | list[Datapoint]],
        calibration_parameters: dict[str, Any],
        calibration_save_function: callable,
        relay_address: int,
        coil_number: int
    ):
        if not (0 <= coil_number < 4):
            raise ValueError(f"Invalid coil number {coil_number} for pump. Coil number must be between 0 and 3 inclusive, corresponding to the 4 outputs of the CS-IO404 relay module.")
        if not (1 <= relay_address <= 247):
            raise ValueError(f"Invalid relay address {relay_address} for pump. MODBUS relay addresses must be between 1 and 247 inclusive.")
        if relay_address == 1:
            logger.warning(f"A pump is configured with relay address 1, which is typically reserved for the controller itself. If your relay module is configured to use address 1, consider changing it to avoid potential conflicts on the MODBUS network.")
        self.bus = bus
        self.db_save_function = db_save_function
        self.calibration_parameters = calibration_parameters
        self.calibration_save_function = calibration_save_function
        self.relay_address = relay_address
        self.coil_number = coil_number

    def doseage_to_time(self, dosage: int) -> float:
        slope = self.calibration_parameters["slope"]
        offset = self.calibration_parameters["offset"]
        return slope * dosage + offset

    async def pumping_callback(self, dosage: int):
        pump_time = self.doseage_to_time(dosage)
        logger.info(f"Starting pump {self.relay_address}-{self.coil_number} for {pump_time} seconds, corresponding to a dosage of {dosage} ml")
        await self._toggle_pump_on_for_duration(pump_time)
        await self.db_save_function(WateringEvent(dosage=dosage))
    
    async def _toggle_pump_on_for_duration(self, time: float):
        self.bus.write_coil(
            address=self.coil_number,
            value=True,
            device_id=self.relay_address
        )
        sleep(time)
        self.bus.write_coil(
            address=self.coil_number,
            value=False,
            device_id=self.relay_address
        )
        logger.info(f"Stopped pump {self.relay_address}-{self.coil_number}")
    
    async def calibrate(self):
        import numpy
        import datetime
        clear_screen()
        print("You will now be guided through calibration of the pump step by step.")
        print("For a robust calibration, the testing setup must be as close as possible to")
        print("the real system setup.")
        print("To that end, first ensure that the following is true:")
        print("")
        print("  - The water tank is filled with water.")
        print("")
        print("  - The pump is submerged in the tank.")
        print("")
        print("  - The pump is connected to the controller.")
        print(f"    (The pump should be connected to output DO{self.coil_number + 1} of the IO404 module, which")
        print(f"    should in turn have the MODBUS address {self.relay_address} and be connected to the RPI.)")
        print("")
        print("  - The outlet tube from the pump is positioned such that it pumps into a")
        print("    measuring vessel at the same height relative to the water tank as it")
        print("    would be were it pumping into the pot of its respective plant.")
        print("")
        print("")
        print("When you've made sure that the above is true, then press enter to continue.")
        print("(The calibration procedure can be cancelled whenever you are prompted for")
        print("input by responding with 'cancel' and pressing enter.)")
        response = input()
        clear_screen()
        match response:
            case 'stop' | 'cancel' | 'quit':
                print("Calibration Aborted.")
                return

        while True:
            print("Measure the height from the water surface in the tank to the outlet of the pump.")
            print("Enter this height in centimeters (rounding up) and press enter.")
            response = input()
            match response:
                case 'stop' | 'cancel' | 'quit':
                    print("Calibration Aborted.")
                    return
            try:
                response = int(response)
                break
            except ValueError:
                clear_screen()
                print(f"The given input '{response}' wasn't a whole number!")
        
        # Time to wait on water in watering tube to recede back into watertank
        rest_time = response / 10 if response > 0 else 0
        clear_screen()

        print("The controller will now go through multiple cycles of turning on the pump for")
        print("different amounts of time. After each cycle you'll have to measure and record")
        print("how much water was actually pumped.")
        print("")
        print("Before continuing ensure that you have a measuring cup with a capacity of")
        print("at least 1 liter, and a way to measure how much water is in that cup down to the")
        print("nearest 10 milliliters.")
        print("")
        print("(Press enter to continue)")
        response = input()
        match response:
            case 'stop' | 'cancel' | 'quit':
                print("Calibration Aborted.")
                return
        clear_screen()
        
        pumped_durations = []
        pumped_amounts = []
        for pumping_time in [time / 2 for time in range(2, 17)]:
            print("Place the measuring cup under the outlet of the pump.")
            print("(Press enter to continue)")
            response = input()
            clear_screen()
            match response:
                case 'stop' | 'cancel' | 'quit':
                    print("Calibration Aborted.")
                    return
            print(f"Pumping... ({pumping_time} seconds)")
            await self._toggle_pump_on_for_duration(pumping_time)
            clear_screen()
            print("Pumping... Done!")
            print("")
            rest_period_start_time = datetime.datetime.now()
            rest_period_end_time = rest_period_start_time + datetime.timedelta(seconds=rest_time)
            while True:
                print("How many milliliters of water was pumped into the measuring cup?.")
                response = input()
                clear_screen()
                match response:
                    case 'stop' | 'cancel' | 'quit':
                        print("Calibration Aborted.")
                        return
                try:
                    response = int(response)
                    if response >= 0:
                        break
                    print("The given input was negative! If the pump is sucking in water, then you've installed it wrong.")
                except Exception:
                    print(f"The given input '{response}' wasn't a whole number!")
            if response > 0:
                logger.debug(f"Recorded pumped amount: {response} ml")
                logger.debug(f"Recorded pumping time: {pumping_time} seconds")
                pumped_amounts.append(response)
                pumped_durations.append(pumping_time)
            else:
                logger.debug("Calibrater recorded a pumped amount of 0ml, discarding this data point.")

            print("Empty the measuring cup.")
            print("(Press enter to continue)")
            response = input()
            clear_screen()
            match response:
                case 'stop' | 'cancel' | 'quit':
                    print("Calibration Aborted.")
                    return
            if (
                remaining_rest_time := (
                    rest_period_end_time - datetime.datetime.now()
                ).total_seconds()
            ) > 0:
                print(f"Waiting for {remaining_rest_time} seconds to let the water in the tube recede back into the tank...")
                await anyio.sleep(remaining_rest_time)
                clear_screen()

        print("Calculating calibration...")
                
        slope, offset = numpy.polyfit(pumped_amounts, pumped_durations, 1)
        old_slope = self.calibration_parameters["slope"]
        old_offset = self.calibration_parameters["offset"]
        self.calibration_parameters["slope"] = slope
        self.calibration_parameters["offset"] = offset
        print("Calibration complete!")
        print("")
        print(f"Old slope: {old_slope}, Old offset: {old_offset}")
        print(f"New slope: {slope}, New offset: {offset}")
        logger.debug(f"Pump {self.relay_address}-{self.coil_number} calibrated with slope {slope} and offset {offset}. Old slope was {old_slope} and old offset was {old_offset}. Calibration data points were: {list(zip(pumped_amounts, pumped_durations))}")
        self.calibration_save_function(slope, offset)
        print("")
        print("The pump is now calibrated. You can test the pump with its new calibration by running the 'test' setup function.")
        print("(Press enter to continue)")
        input()

    async def test_pump(self):
        print("How many ml do you want to pump for the test?")
        while True:
            try:
                dosage = int(input("Enter dosage in ml: "))
                break
            except ValueError:
                print("Invalid input. Please enter an integer value for the dosage.")
        pump_time = self.doseage_to_time(dosage)
        logger.info(f"Starting pump {self.relay_address}-{self.coil_number} for {pump_time} seconds, corresponding to a dosage of {dosage} ml")
        await self._toggle_pump_on_for_duration(pump_time)

    def setup_functions(self) -> dict[str, dict[str, any]]:
        return {
            "calibrate": {
                "description": "Run the calibration procedure for the pump.",
                "function": self.calibrate
            },
            "test": {
                "description": "Test the pump by running it for a short time.",
                "function": self.test_pump
            }
        }