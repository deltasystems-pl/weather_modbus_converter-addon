from __future__ import annotations

from dataclasses import dataclass

from .config import ALLOWED_PROTOCOL_MODES
from .decode import (
    HISTORY_BLOCKS,
    HISTORY_SAMPLES,
    ON_DEMAND_REGISTERS,
    REGISTER_COUNT,
    START_REGISTER,
    decode_history_blocks,
    decode_identity,
    decode_on_demand,
)

IDENTITY_START_REGISTER = 0x0160
IDENTITY_REGISTER_COUNT = 5


class ModbusReadError(RuntimeError):
    pass


@dataclass
class Ws90ModbusClient:
    host: str
    port: int = 502
    unit_id: int = 144
    protocol_mode: str = "rtu_over_tcp"
    timeout_seconds: float = 3.0

    def read_registers(self) -> list[int]:
        return self.read_register_range(START_REGISTER, REGISTER_COUNT)

    def read_registers_single(self) -> list[int]:
        return [self.read_register(address) for address in range(START_REGISTER, START_REGISTER + REGISTER_COUNT)]

    def read_identity(self) -> dict[str, object]:
        return decode_identity(self.read_register_range(IDENTITY_START_REGISTER, IDENTITY_REGISTER_COUNT))

    def read_on_demand(self) -> dict[str, object]:
        raw_values = {
            name: self.read_register(address)
            for name, (address, _scale) in ON_DEMAND_REGISTERS.items()
        }
        return decode_on_demand(raw_values)

    def read_history(self) -> dict[str, list[dict[str, object]]]:
        raw_blocks = {
            name: self.read_register_range(address, HISTORY_SAMPLES)
            for name, (address, _scale) in HISTORY_BLOCKS.items()
        }
        return decode_history_blocks(raw_blocks)

    def read_register(self, address: int) -> int:
        return self.read_register_range(address, 1)[0]

    def read_register_range(self, address: int, count: int) -> list[int]:
        if self.protocol_mode not in ALLOWED_PROTOCOL_MODES:
            allowed = ", ".join(ALLOWED_PROTOCOL_MODES)
            raise ModbusReadError(f"Unsupported protocol_mode {self.protocol_mode!r}. Valid values: {allowed}")
        try:
            from pymodbus.client import ModbusTcpClient
            from pymodbus.exceptions import ModbusException
            from pymodbus.framer import FramerType
        except ModuleNotFoundError as exc:
            raise ModbusReadError("pymodbus is required for Modbus polling; install requirements.txt") from exc

        framer = FramerType.RTU if self.protocol_mode == "rtu_over_tcp" else FramerType.SOCKET
        client = ModbusTcpClient(
            self.host,
            port=self.port,
            timeout=self.timeout_seconds,
            retries=0,
            framer=framer,
        )
        try:
            if not client.connect():
                raise ModbusReadError(f"Could not connect to {self.host}:{self.port}")
            try:
                response = client.read_holding_registers(
                    address=address,
                    count=count,
                    device_id=self.unit_id,
                )
            except TypeError:
                response = client.read_holding_registers(
                    address,
                    count=count,
                    slave=self.unit_id,
                )
            if response.isError():
                raise ModbusReadError(f"Modbus exception response: {response}")
            return list(response.registers)
        except ModbusException as exc:
            raise ModbusReadError(str(exc)) from exc
        finally:
            client.close()
