"""Alta privada de usuarios; las contraseñas nunca se reciben como argumentos."""

import argparse
import getpass
import sys
from typing import Never

from pydantic import TypeAdapter, ValidationError

from monetae.api.schemas.auth import Currency, Email
from monetae.config import Settings
from monetae.db.session import create_session_factory
from monetae.services.auth import AuthService, SystemClock


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        # Unknown argument values may be passwords mistakenly supplied on the command line.
        self.exit(2, "Invalid command arguments. Use --help; passwords require stdin or getpass.\n")


def main(argv: list[str] | None = None) -> int:
    parser = SafeArgumentParser(prog="monetae", allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-user", allow_abbrev=False)
    create.add_argument("--email", required=True)
    create.add_argument("--base-currency", default="PEN")
    create.add_argument("--locale", choices=["es", "en"], default="es")
    create.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args(argv)
    try:
        email = TypeAdapter(Email).validate_python(args.email, strict=True)
        currency = TypeAdapter(Currency).validate_python(args.base_currency, strict=True)
        if args.password_stdin:
            password = sys.stdin.readline(1024).rstrip("\r\n")
        else:
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Confirm password: "):
                raise ValueError("Passwords do not match.")
        config = Settings()
        with create_session_factory(config)() as db:
            AuthService(db, config, SystemClock()).create_user(
                email, password, currency, args.locale
            )
            db.commit()
    except ValidationError:
        print("Invalid user configuration.", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("User created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
