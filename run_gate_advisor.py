"""CLI compatibility wrapper for the gate dossier reviewer."""
import argparse
import json
from pathlib import Path
from backend.domain.gates import GateInputError, VERSION, evaluate, nonempty, numeric, stamp


def main():
    parser = argparse.ArgumentParser(
        description='Rà soát hồ sơ lập kế hoạch cống; không phát lệnh vận hành.'
    )
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(
        json.loads(args.policy.read_text(encoding='utf-8-sig')),
        json.loads(args.input.read_text(encoding='utf-8-sig')),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
