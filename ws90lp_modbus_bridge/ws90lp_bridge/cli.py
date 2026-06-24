from __future__ import annotations

import argparse
import logging
import sys

import yaml

from .config import load_config, redact_config
from .decode import STATE_FIELDS
from .service import BridgeService, poll_once, state_json
from .modbus import Ws90ModbusClient


COMMON_OPTIONS = ("host", "port", "unit_id", "protocol_mode", "live_read_mode", "poll_interval_seconds", "log_level")


def add_common_options(command: argparse.ArgumentParser) -> None:
    command.add_argument("--config", dest="command_config", help="YAML or JSON config file")
    command.add_argument("--host")
    command.add_argument("--port", type=int)
    command.add_argument("--unit-id", type=int)
    command.add_argument("--protocol-mode", choices=["rtu_over_tcp", "modbus_tcp_gateway"])
    command.add_argument("--live-read-mode", choices=["block", "single"])
    command.add_argument("--poll-interval-seconds", type=float)
    command.add_argument("--log-level")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ws90lp-bridge")
    parser.add_argument("--config", help="YAML or JSON config file")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("poll-once", "run", "dump-config", "read-identity", "read-on-demand", "read-history"):
        command = sub.add_parser(name)
        add_common_options(command)
    read_field = sub.add_parser("read-field", help="Read one decoded field once and print only that value")
    add_common_options(read_field)
    read_field.add_argument("field", nargs="?", choices=STATE_FIELDS, help="Decoded field name to print")
    read_field.add_argument("--list-fields", action="store_true", help="List readable decoded field names")
    return parser


def _overrides(args: argparse.Namespace) -> dict[str, object]:
    return {key: getattr(args, key, None) for key in COMMON_OPTIONS}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = getattr(args, "command_config", None) or args.config
    config = load_config(config_path, _overrides(args))
    logging.basicConfig(level=getattr(logging, config.log_level, logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.command == "poll-once":
        print(state_json(poll_once(config)))
        return 0
    if args.command in {"read-identity", "read-on-demand", "read-history"}:
        if not config.host:
            raise ValueError("host is required")
        client = Ws90ModbusClient(
            host=config.host,
            port=config.port,
            unit_id=config.unit_id,
            protocol_mode=config.protocol_mode,
            timeout_seconds=config.timeout_seconds,
        )
        if args.command == "read-identity":
            print(state_json(client.read_identity()))
            return 0
        if args.command == "read-on-demand":
            print(state_json(client.read_on_demand()))
            return 0
        print(state_json(client.read_history()))
        return 0
    if args.command == "read-field":
        if args.list_fields:
            print("\n".join(STATE_FIELDS))
            return 0
        if not args.field:
            print("read-field requires a field name. Use --list-fields to see valid names.", file=sys.stderr)
            return 2
        state = poll_once(config)
        value = state[args.field]
        print("" if value is None else value)
        return 0
    if args.command == "dump-config":
        print(yaml.safe_dump(redact_config(config), sort_keys=False))
        return 0
    if args.command == "run":
        BridgeService(config).run()
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
