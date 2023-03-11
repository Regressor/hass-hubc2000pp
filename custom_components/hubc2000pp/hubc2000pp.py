"""The HUB-C2000PP service utils."""

import asyncio
from contextlib import suppress
import logging
import socket
from typing import Any

import aioudp

SEP_STRING = "__DLM__"

_LOGGER = logging.getLogger(__name__)
LISTEN_ADDRESS = "0.0.0.0"


def update_device(message, devices):
    """Parse push message from hub, find and update device."""
    push_data = message.split(":")

    # message format: "type:uid:state" (type can be zone, relay, part)
    if len(push_data) == 3:
        uid = push_data[1]
        state = push_data[2]
        if push_data[0] == "zone":
            zones = devices["zones"]
            zone = next((x for x in zones if x["uid"] == uid), None)
            if zone:
                zone["state"] = state

        if push_data[0] == "part":
            parts = devices["parts"]
            part = next((x for x in parts if x["id"] == int(uid)), None)
            if part:
                part["stat"] = state

        if push_data[0] == "relay":
            relays = devices["relays"]
            relay = next((x for x in relays if x["id"] == int(uid)), None)
            if relay:
                relay["stat"] = state


async def switch_relay(relay: int, state: bool, host: str, port: int) -> bool:
    """Switch relay on or off."""
    try:
        async with aioudp.connect(host, port) as connection:
            # first is "BAD_CMD" because of "trash" from aioudp
            result = await asyncio.wait_for(connection.recv(), timeout=1)

            if state:
                cmd = f"relay_on:{relay}".encode()
            else:
                cmd = f"relay_off:{relay}".encode()

            await connection.send(cmd)
            result = await asyncio.wait_for(connection.recv(), timeout=1)
            reply = result.decode("utf-8")

            if reply != "RELAY_OK":
                return False

            return True
    except asyncio.TimeoutError:
        return False


class RelayFailed(Exception):
    """Raised when an switching relay has failed."""


async def arm_partition(part, host, port) -> bool:
    """ARM specified partition."""
    try:
        async with aioudp.connect(host, port) as connection:
            # first is "BAD_CMD" because of "trash" from aioudp
            result = await asyncio.wait_for(connection.recv(), timeout=1)

            await connection.send(f"arm:{part}".encode())
            result = await asyncio.wait_for(connection.recv(), timeout=1)
            reply = result.decode("utf-8")

            if reply != "ARM_OK":
                return False

            return True
    except asyncio.TimeoutError:
        return False


async def disarm_partition(part, host, port) -> bool:
    """DISARM specified partition."""
    try:
        async with aioudp.connect(host, port) as connection:
            # first is "BAD_CMD" because of "trash" from aioudp
            result = await asyncio.wait_for(connection.recv(), timeout=1)

            await connection.send(f"disarm:{part}".encode())
            result = await asyncio.wait_for(connection.recv(), timeout=1)
            reply = result.decode("utf-8")

            if reply != "DISARM_OK":
                return False

            return True
    except asyncio.TimeoutError:
        return False


class ArmFailed(Exception):
    """Raised when an arm has failed."""


class DisarmFailed(Exception):
    """Raised when a disarm has failed."""


async def get_devices(host, port):
    """Get devices from HUB-C2000PP service."""
    devices = {"zones": [], "relays": [], "parts": [], "error": False}

    try:
        async with aioudp.connect(host, port) as connection:
            # first is "BAD_CMD" because of "trash" from aioudp
            result = await asyncio.wait_for(connection.recv(), timeout=1)

            await connection.send(b"getZones")
            result = await asyncio.wait_for(connection.recv(), timeout=1)
            result = result.decode("utf-8")

            if result == "BAD_CMD":
                devices["error"] = "Server returned BAD_CMD"
                return devices

            if result:
                lines = result.split(SEP_STRING)
                for line in lines:
                    device_info = line.split(":")
                    if len(device_info) == 10:
                        if device_info[0] == "zone":
                            uid = f"{int(device_info[1])}.{device_info[2]}.{device_info[3]}.{device_info[4]}"
                            adc = device_info[6]
                            if adc and adc != "-":
                                adc = round(float(device_info[6]), 2)
                            device = {
                                "id": int(device_info[1]),
                                "sh": device_info[2],
                                "part": device_info[3],
                                "stype": device_info[4],
                                "state": device_info[5],
                                "adc": adc,
                                "type": device_info[7],
                                "dev": device_info[8],
                                "desc": device_info[9],
                                "uid": uid,
                            }
                            devices["zones"].append(device)
                            continue

                    devices["error"] = "Unexpected server reply"

            await connection.send(b"getParts")
            result = await asyncio.wait_for(connection.recv(), timeout=1)
            result = result.decode("utf-8")

            if result == "BAD_CMD":
                devices["error"] = "Server returned BAD_CMD"
                return devices

            if result:
                lines = result.split(SEP_STRING)
                for line in lines:
                    device_info = line.split(":")
                    if len(device_info) == 4:
                        if device_info[0] == "part":
                            uid = f"partition_{int(device_info[1])}"
                            device = {
                                "id": int(device_info[1]),
                                "stat": device_info[2],
                                "desc": device_info[3],
                                "uid": uid,
                            }
                            if device["stat"] == 0:
                                continue
                            devices["parts"].append(device)
                            continue

                    devices["error"] = "Unexpected server reply"

            await connection.send(b"getRelays")
            result = await asyncio.wait_for(connection.recv(), timeout=1)
            result = result.decode("utf-8")

            if result == "BAD_CMD":
                devices["error"] = "Server returned BAD_CMD"
                return devices

            if result:
                lines = result.split(SEP_STRING)
                for line in lines:
                    device_info = line.split(":")
                    if len(device_info) == 4:
                        if device_info[0] == "relay":
                            device = {
                                "id": int(device_info[1]),
                                "stat": device_info[2],
                                "desc": device_info[3],
                            }
                            devices["relays"].append(device)
                            continue

                    devices["error"] = "Unexpected server reply"

        return devices
    except asyncio.TimeoutError:
        devices["error"] = "Connection timeout"
        return devices


def create_udp_socket(host, port, blocking=True) -> socket.socket | None:
    """Create and bind an udp socket for communication."""
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp_socket.setblocking(blocking)
    udp_socket.bind((host, port))
    return udp_socket


class HUBC2000PPUdpReceiver:
    """Async UDP communication class for HUBC2000PP."""

    def __init__(self, port=22000) -> None:
        """Init receiver data."""
        self._protocol = None
        self._port = port
        self._registered_callbacks: dict[Any, Any] = {}

    def _create_udp_listener(self):
        """Create the UDP multicast socket and protocol."""
        udp_socket = create_udp_socket(LISTEN_ADDRESS, self._port, blocking=False)
        loop = asyncio.get_event_loop()
        return loop.create_datagram_endpoint(
            lambda: self.UdpListenerProtocol(loop, udp_socket, self),
            sock=udp_socket,
        )

    @property
    def registered_callbacks(self):
        """Return the callbacks."""
        return self._registered_callbacks

    def register_hub(self, ip, callback):
        """Register a HUB to this udp listener."""
        if ip in self._registered_callbacks:
            _LOGGER.error("A callback for ip '%s' already registered, overwriting!", ip)
        self._registered_callbacks[ip] = callback

    def unregister_hub(self, ip):
        """Unregister a HUB from this udp listener."""
        if ip in self._registered_callbacks:
            self._registered_callbacks.pop(ip)

    async def start_listen(self):
        """Start listening."""
        if self._protocol is not None:
            _LOGGER.error("Udp listener already started, not starting another one")
            return

        _, self._protocol = await self._create_udp_listener()

    def stop_listen(self):
        """Stop listening."""
        if self._protocol is None:
            return

        self._protocol.close()
        self._protocol = None

    class UdpListenerProtocol:
        """Handle received udp messages."""

        def __init__(self, loop, udp_socket, parent) -> None:
            """Initialize the class."""
            self.transport = None
            self._loop = loop
            self._sock = udp_socket
            self._parent = parent
            self._connected = False

        def connection_made(self, transport):
            """Set the transport."""
            self.transport = transport
            self._connected = True
            _LOGGER.info("HUBC2000PP udp listener started")

        def connection_lost(self, exc):
            """Handle connection lost."""
            if self._connected:
                _LOGGER.error("Connection lost in HUBC2000PP udp listener: %s", exc)

        def datagram_received(self, data, addr):
            """Handle received messages."""
            try:
                (ip_add, _) = addr
                message = data.decode("utf-8")

                if ip_add not in self._parent.registered_callbacks:
                    _LOGGER.info("Unknown hub ip %s", ip_add)
                    return

                callback = self._parent.registered_callbacks[ip_add]
                callback(message)

            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Cannot process hub udp message: '%s'", data)

        def error_received(self, exc):
            """Log UDP errors."""
            _LOGGER.error("UDP error received in HUBC2000PP udp listener: %s", exc)

        def close(self):
            """Stop the server."""
            _LOGGER.debug("HUBC2000PP udp listener shutting down")
            self._connected = False
            if self.transport:
                self.transport.close()

            with suppress(NotImplementedError):
                self._loop.remove_writer(self._sock.fileno())
                self._loop.remove_reader(self._sock.fileno())

            self._sock.close()
            _LOGGER.info("HUBC2000PP listener stopped")
