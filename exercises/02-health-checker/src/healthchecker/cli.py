from calendar import error
from typing import Annotated, Any

import typer
import sys
from pathlib import Path
import yaml
from healthchecker.logger import get_logger
from healthchecker.models import CheckConfig

logger = get_logger(__name__)

app = typer.Typer(
    add_completion=True,
    help="Perform health check on specific endpoints with retry ability.",
)

@app.command()
def main(
    check: Annotated[
        str | None,
        typer.Option(
            default="--check",
            help="Check single endpoint, use for debugging purposes.",

        )
    ],
    config_file: Annotated[
        Path,
        typer.Option(
            default="--config",
            help="Path to config file",
        )
    ]
) -> None:
    try:
        config = yaml.safe_load(open(config_file))
        try:
            check_config = CheckConfig(**config)
            checks = check_config.checks
            if check not in [check.name for check in checks]:
                logger.error('check.validation',extra={'error': 'check value is not valid'})
                sys.exit(1)



        except Exception as e:
            sys.exit(1)

    except FileNotFoundError as e:
        logger.error('cli.validation', extra={'config_file': config_file, 'error': f'File not found: {e}'})
        sys.exit(2)
    except yaml.YAMLError as e:
        logger.error('cli.validation', extra={'config_file': config_file, 'error': f'YAML error: {e}'})
        sys.exit(2)
    except Exception as e:
        logger.error('cli.validation', extra={'config_file': config_file, 'error': e})
        sys.exit(2)



    raise NotImplementedError()

__all__ = ["app", "main"]