import importlib
import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMMANDS = {
    ("weather", "update"): ("tools.weather_inputs", "main"),
    ("feature", "hydrology-study"): ("scripts.experiment_ec_long_hydrology", "main"),
    ("model", "train"): ("tools.model_training", "main"),
    ("model", "package-rf"): ("scripts.rf_compact_artifacts", "main"),
    ("backtest", "rolling"): ("tools.backtest_protocols", "main"),
    ("observation", "verify-mrc"): ("tools.observation_cleaning", "main"),
    ("security", "roles"): ("tools.security_setup", "main"),
    ("security", "field-keys"): ("tools.security_setup", "main"),
    ("source", "fes"): ("scripts.utilities.collect_fes2022b", "main"),
}


def run_checks(full=False):
    python = PROJECT_ROOT / ".venv/Scripts/python.exe"
    if not python.is_file():
        raise FileNotFoundError("Missing .venv/Scripts/python.exe")
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    python_command = [str(python), "-m", "unittest"]
    if full:
        python_command.extend(["discover", "-s", "tests", "-p", "test_*.py"])
    else:
        python_command.extend([
            "tests.test_model_loading", "tests.test_backend_audit", "tests.test_security",
            "tests.test_spatial_inputs_cache", "tests.test_dss_storage_errors",
            "tests.test_sql_migrations",
        ])
    status = subprocess.run(python_command, cwd=PROJECT_ROOT, env=environment, check=False).returncode
    if status:
        return status
    return subprocess.run([
        "node", "--test", "tests/gate_intake_rules.test.mjs",
        "tests/river_interpolation.test.mjs",
    ], cwd=PROJECT_ROOT, env=environment, check=False).returncode


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in ("-h", "--help"):
        print("usage: python -m tools <group> <command> [options]")
        print("commands:")
        for group, command in sorted(COMMANDS):
            print(f"  {group} {command}")
        print("  check smoke | check full")
        return 0 if arguments else 2
    if arguments[0] == "check":
        if len(arguments) > 2 or (len(arguments) == 2 and arguments[1] not in ("smoke", "full")):
            raise SystemExit("Use: python -m tools check smoke|full")
        return run_checks(len(arguments) == 2 and arguments[1] == "full")
    if len(arguments) < 2 or tuple(arguments[:2]) not in COMMANDS:
        raise SystemExit("Unknown command. Run python -m tools --help")
    group, command = arguments[:2]
    module_name, function_name = COMMANDS[(group, command)]
    action = getattr(importlib.import_module(module_name), function_name)
    action_arguments = arguments[2:]
    if group == "security":
        action_arguments.insert(0, command)
    result = action(action_arguments)
    return 0 if result is None else result
