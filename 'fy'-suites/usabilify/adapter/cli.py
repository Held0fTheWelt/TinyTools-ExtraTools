from fy_platform.ai.adapter_cli_helper import run_adapter_cli
from usabilify.adapter.service import UsabilifyAdapter


def main(argv=None) -> int:
    return int(run_adapter_cli(UsabilifyAdapter, argv))


if __name__ == "__main__":
    raise SystemExit(main())

