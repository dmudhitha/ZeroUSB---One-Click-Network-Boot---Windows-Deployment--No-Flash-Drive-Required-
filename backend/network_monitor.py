import time
import threading
import psutil
from typing import Dict, List, Tuple, Callable, Optional

class NetworkMonitor:
    def __init__(self, interface: str = "enp3s0", history_len: int = 60):
        self.interface = interface
        self.history_len = history_len
        self.history_tx: List[float] = [0.0] * history_len  # Bytes/sec
        self.history_rx: List[float] = [0.0] * history_len  # Bytes/sec
        
        self.current_tx_speed = 0.0  # Bytes/sec
        self.current_rx_speed = 0.0  # Bytes/sec
        self.peak_tx_speed = 0.0
        self.total_tx_bytes = 0
        self.total_rx_bytes = 0
        
        self._prev_tx = 0
        self._prev_rx = 0
        self._prev_time = time.time()
        self._is_running = False
        self._lock = threading.Lock()
        self._subscribers: List[Callable[[Dict[str, float]], None]] = []

    def set_interface(self, interface: str):
        with self._lock:
            self.interface = interface
            self._prev_tx = 0
            self._prev_rx = 0

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        self._prev_time = time.time()
        
        # Initialize initial bytes
        io = self._get_io(self.interface)
        if io:
            self._prev_tx = io.bytes_sent
            self._prev_rx = io.bytes_recv

        thread = threading.Thread(target=self._worker, daemon=True)
        thread.start()

    def stop(self):
        self._is_running = False

    def subscribe(self, callback: Callable[[Dict[str, float]], None]):
        self._subscribers.append(callback)

    def _worker(self):
        while self._is_running:
            time.sleep(0.5)
            now = time.time()
            dt = now - self._prev_time
            if dt <= 0:
                continue

            io = self._get_io(self.interface)
            if io:
                curr_tx = io.bytes_sent
                curr_rx = io.bytes_recv

                if self._prev_tx > 0 and self._prev_rx > 0:
                    delta_tx = max(0, curr_tx - self._prev_tx)
                    delta_rx = max(0, curr_rx - self._prev_rx)

                    tx_speed = delta_tx / dt
                    rx_speed = delta_rx / dt

                    with self._lock:
                        self.current_tx_speed = tx_speed
                        self.current_rx_speed = rx_speed
                        self.total_tx_bytes += delta_tx
                        self.total_rx_bytes += delta_rx

                        if tx_speed > self.peak_tx_speed:
                            self.peak_tx_speed = tx_speed

                        self.history_tx.append(tx_speed)
                        self.history_rx.append(rx_speed)
                        if len(self.history_tx) > self.history_len:
                            self.history_tx.pop(0)
                        if len(self.history_rx) > self.history_len:
                            self.history_rx.pop(0)

                    # Notify subscribers
                    stats = self.get_stats()
                    for sub in self._subscribers:
                        try:
                            sub(stats)
                        except Exception:
                            pass

                self._prev_tx = curr_tx
                self._prev_rx = curr_rx
                self._prev_time = now

    def _get_io(self, iface: str):
        try:
            counters = psutil.net_io_counters(pernic=True)
            if iface in counters:
                return counters[iface]
            # Fallback to total system network
            return psutil.net_io_counters(pernic=False)
        except Exception:
            return None

    def get_stats(self) -> Dict[str, float]:
        with self._lock:
            return {
                "tx_speed": self.current_tx_speed,
                "rx_speed": self.current_rx_speed,
                "peak_tx": self.peak_tx_speed,
                "total_tx": self.total_tx_bytes,
                "total_rx": self.total_rx_bytes,
                "history_tx": list(self.history_tx),
                "history_rx": list(self.history_rx),
            }
