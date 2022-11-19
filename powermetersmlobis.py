from threading import Thread, Event
from typing import Optional, Callable, List, Dict

import logging
from serial import Serial, SerialException
from smllib import SmlStreamReader
from smllib.errors import SmlLibException
from smllib.sml import SmlListEntry

logger = logging.getLogger().getChild(__name__)


class ObisMeta:
    obis_short: str
    unit_code: int
    identifier: str
    meta_scaler: int
    unit: str

    def __init__(self, obis_short: str, unit_code: int, identifier: str, meta_scaler: int, unit: str):
        self.obis_short = obis_short
        self.unit_code = unit_code
        self.identifier = identifier
        self.meta_scaler = meta_scaler
        self.unit = unit


class ObisValue:
    sml_raw: SmlListEntry
    meta: Optional[ObisMeta]
    numeric_value: Optional[float]
    string_value: Optional[str]

    def __init__(self, sml_raw: SmlListEntry):
        self.sml_raw = sml_raw

        obis_short = sml_raw.obis.obis_short
        unit_code = sml_raw.unit
        value_scaler = sml_raw.scaler
        value = sml_raw.value

        self.meta = _OBIS_METAS_BY_OBIS_SHORT.get(obis_short)
        if self.meta is not None and self.meta.unit_code != unit_code:
            self.meta = None

        if self.meta is not None and self.meta.unit_code is not None and value_scaler is not None:
            scaler = value_scaler + self.meta.meta_scaler
        else:
            scaler = None

        if scaler is not None:
            value *= 10 ** scaler
            self.numeric_value = value
            value_format = "{:." + str(max(0, -scaler)) + "f}"
        else:
            value_format = "{}"

        self.string_value = value_format.format(value)

    def __str__(self) -> str:
        obis_short = self.sml_raw.obis.obis_short
        if self.meta is not None:
            identifier = self.meta.identifier
            unit = self.meta.unit
        else:
            identifier = "<unknown>"
            unit = "" if self.sml_raw.unit is None else self.sml_raw.unit

        return f"{obis_short:8} {identifier:25} {self.string_value:>20} {unit}"


# Unit codes:
_UC_WATT_HOUR = 30
_UC_WATT = 27
_UC_VOLT = 35
_UC_AMPERE = 33
_UC_HERTZ = 44
_UC_DEGREE = 8

# Known OBIS value meta data infos:
_OBIS_METAS = [
    ObisMeta("1.8.0", _UC_WATT_HOUR, "energy_import", -3, "kWh"),
    ObisMeta("1.8.1", _UC_WATT_HOUR, "energy_import_tariff_1", -3, "kWh"),
    ObisMeta("1.8.2", _UC_WATT_HOUR, "energy_import_tariff_2", -3, "kWh"),
    ObisMeta("2.8.0", _UC_WATT_HOUR, "energy_export", -3, "kWh"),
    ObisMeta("16.7.0", _UC_WATT, "active_power", 0, "W"),
    ObisMeta("36.7.0", _UC_WATT, "active_power_l1", 0, "W"),
    ObisMeta("56.7.0", _UC_WATT, "active_power_l2", 0, "W"),
    ObisMeta("76.7.0", _UC_WATT, "active_power_l3", 0, "W"),
    ObisMeta("12.7.0", _UC_VOLT, "voltage", 0, "V"),
    ObisMeta("32.7.0", _UC_VOLT, "voltage_l1", 0, "V"),
    ObisMeta("52.7.0", _UC_VOLT, "voltage_l2", 0, "V"),
    ObisMeta("72.7.0", _UC_VOLT, "voltage_l3", 0, "V"),
    ObisMeta("11.7.0", _UC_AMPERE, "current", 0, "A"),
    ObisMeta("31.7.0", _UC_AMPERE, "current_l1", 0, "A"),
    ObisMeta("51.7.0", _UC_AMPERE, "current_l2", 0, "A"),
    ObisMeta("71.7.0", _UC_AMPERE, "current_l3", 0, "A"),
    ObisMeta("14.7.0", _UC_HERTZ, "frequency", 0, "Hz"),
    ObisMeta("81.7.1", _UC_DEGREE, "phase_voltage_l2_l1", 0, "°"),
    ObisMeta("81.7.2", _UC_DEGREE, "phase_voltage_l3_l1", 0, "°"),
    ObisMeta("81.7.4", _UC_DEGREE, "phase_current_voltage_l1", 0, "°"),
    ObisMeta("81.7.15", _UC_DEGREE, "phase_current_voltage_l2", 0, "°"),
    ObisMeta("81.7.26", _UC_DEGREE, "phase_current_voltage_l3", 0, "°"),
]

_OBIS_METAS_BY_OBIS_SHORT = dict()
for obis_meta in _OBIS_METAS:
    _OBIS_METAS_BY_OBIS_SHORT[obis_meta.obis_short] = obis_meta


class PowerMeterSmlObisReader:
    _thread: Optional[Thread]
    _running_event: Event
    _receive_callbacks: List[Callable[['PowerMeterSmlObisReader'], None]]

    _serial_factory: Callable[[], Serial]
    _serial: Optional[Serial]

    _reader: SmlStreamReader

    values: List[ObisValue]
    values_by_id: Dict[str, ObisValue]

    def __init__(self,
                 serial_factory: Callable[[], Serial]):
        super().__init__()
        self._thread = None
        self._running_event = Event()
        self._receive_callbacks = []
        self._serial_factory = serial_factory
        self._serial = None
        self.values = []
        self.values_by_id = dict()

    def add_callback(self, callback: Callable[['PowerMeterSmlObisReader'], None]) -> None:
        self._receive_callbacks.append(callback)

    def start(self) -> None:
        if self._thread is None:
            self._reader = SmlStreamReader()
            self._running_event.set()
            self._thread = Thread(target=self._run)
            self._thread.start()

    def stop(self) -> None:
        if self._thread is not None:
            self._running_event.clear()
            self._thread = None

    def _fire_received(self) -> None:
        for callback in self._receive_callbacks:
            callback(self)

    def _run(self) -> None:
        logger.info("Starting acquisition of power meter SML OBIS values")
        while self._running_event.is_set():
            try:
                self._step()
            except Exception as err:
                logger.exception("Unexpected exception ", err)
        self._close_serial()
        logger.info("Stopped acquisition of power meter SML OBIS values")

    def _step(self) -> None:
        self._open_serial()
        try:
            data = self._serial.read()
        except SerialException as err:
            self._close_serial()
            return

        self._reader.add(data)
        try:
            frame = self._reader.get_frame()
            if frame is None:
                return

            frame.parse_frame()
            sml_raws = frame.get_obis()

            values = []
            values_by_id = dict()

            for sml_raw in sml_raws:
                obis_value = ObisValue(sml_raw)
                values.append(obis_value)
                if obis_value.meta is not None:
                    values_by_id[obis_value.meta.identifier] = obis_value

            self.values = values
            self.values_by_id = values_by_id

            self._fire_received()

        except SmlLibException as err:
            logger.exception("SML decoding error", err)

    def _open_serial(self) -> None:
        if self._serial is None:
            self._serial = self._serial_factory()

    def _close_serial(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None


if __name__ == "__main__":

    def _print_callback(reader: PowerMeterSmlObisReader):
        print("--------------------------------------------------------------")
        for value in reader.values:
            print(value)


    def _serial_factory():
        return Serial(port="/dev/ttyUSB0", baudrate=9600)


    reader = PowerMeterSmlObisReader(serial_factory=_serial_factory)
    reader.add_callback(_print_callback)
    reader.start()
