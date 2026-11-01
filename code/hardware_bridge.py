from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import time

try:
    import serial
    from serial.tools import list_ports
except Exception:
    serial = None
    list_ports = None


@dataclass
class FanControllerConfig:
    mock: bool = True                 # Skip serial communication in mock mode.
    channels: int = 3                 # number of fans
    baud: int = 115200
    port: Optional[str] = None        # None selects the first detected device.
    startup_delay_s: float = 2.0      # Arduino reset delay


class FanController:
    """
    Sends PWM values to Arduino over Serial as: "v1,v2,v3\n" (0..255 each).
    If mock=True, does nothing (safe for running dashboard without hardware).
    """

    def __init__(self, cfg: FanControllerConfig):
        self.cfg = cfg
        self._ser = None
        self._last = [0] * cfg.channels

        if self.cfg.mock:
            return

        if serial is None:
            raise RuntimeError("pyserial not installed. Run: pip install pyserial")

        port = self.cfg.port or self._auto_detect_port()
        if not port:
            raise RuntimeError(
                "Could not auto-detect Arduino port. "
                "Unplug/replug Arduino and set FanControllerConfig(port='...')."
            )

        self._ser = serial.Serial(port, self.cfg.baud, timeout=1)
        time.sleep(self.cfg.startup_delay_s)  # let Arduino reboot after serial open

    def _auto_detect_port(self) -> Optional[str]:
        if list_ports is None:
            return None
        candidates = []
        for p in list_ports.comports():
            name = (p.device or "").lower()
            desc = (p.description or "").lower()

            # common mac ports: /dev/cu.usbmodem*, /dev/cu.usbserial*
            if "usbmodem" in name or "usbserial" in name:
                candidates.append(p.device)

            # CH340/CP210x clones sometimes show in description
            if "ch340" in desc or "cp210" in desc or "arduino" in desc:
                candidates.append(p.device)

        
        seen = set()
        uniq = []
        for c in candidates:
            if c and c not in seen:
                uniq.append(c)
                seen.add(c)

        return uniq[0] if uniq else None

    def set_pwms(self, values: List[int]) -> None:
        if len(values) != self.cfg.channels:
            raise ValueError(f"Expected {self.cfg.channels} values, got {len(values)}")

        vals = [int(max(0, min(255, v))) for v in values]
        self._last = vals

        if self.cfg.mock:
            return

        if not self._ser:
            raise RuntimeError("Serial not initialized")

        line = (",".join(str(v) for v in vals) + "\n").encode("ascii")
        self._ser.write(line)

    def stop_all(self) -> None:
        self.set_pwms([0] * self.cfg.channels)

    def close(self) -> None:
        try:
            if self._ser:
                self.stop_all()
                self._ser.close()
        finally:
            self._ser = None
