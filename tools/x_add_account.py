#!/usr/bin/env python3
"""Add an X account to Otto's broadcast system.

Usage (cookie auth — from browser):
  python3 ~/otto/tools/x_add_account.py @handle --cookies AUTH_TOKEN CT0

Usage (login auth — username/password):
  python3 ~/otto/tools/x_add_account.py @handle --login USERNAME PASSWORD [--email EMAIL]

The credentials are stored in the broadcast platform config.
"""

import argparse
import json
from pathlib import Path

CONFIG_PATH = Path("/home/web3relic/otto/projects/broadcast/configs/platforms.json")


def main():
    parser = argparse.ArgumentParser(description="Add an X account to Otto's broadcast system")
    parser.add_argument("handle", help="X handle (with or without @)")

    sub = parser.add_subparsers(dest="method")

    cookie_parser = sub.add_parser("--cookies", help="Use browser cookies")
    cookie_parser.add_argument("auth_token", help="auth_token cookie value")
    cookie_parser.add_argument("ct0", help="ct0 cookie value")

    login_parser = sub.add_parser("--login", help="Use username/password")
    login_parser.add_argument("username", help="X username")
    login_parser.add_argument("password", help="X password")
    login_parser.add_argument("--email", help="Email (recommended for 2FA)", default="")

    args = parser.parse_args()
    handle = args.handle.lstrip("@")

    if not args.method:
        # Try positional args for backwards compat: x_add_account.py @handle AUTH_TOKEN CT0
        import sys
        if len(sys.argv) == 4:
            auth_token = sys.argv[2]
            ct0 = sys.argv[3]
            _upsert_account(handle, {"auth_token": auth_token, "ct0": ct0})
            return
        parser.print_help()
        print("\nQuick cookie mode:  python3 x_add_account.py @handle AUTH_TOKEN CT0")
        print("\nTo get cookies from your browser:")
        print("1. Login to X on your browser")
        print("2. Open DevTools (F12) -> Application -> Cookies -> https://x.com")
        print("3. Copy 'auth_token' and 'ct0' values")
        return

    if args.method == "--cookies":
        _upsert_account(handle, {"auth_token": args.auth_token, "ct0": args.ct0})
    elif args.method == "--login":
        _upsert_account(handle, {
            "username": args.username,
            "password": args.password,
            "email": args.email,
        })


def _upsert_account(handle: str, creds: dict):
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    accounts = config["platforms"]["x"]["accounts"]

    for i, acc in enumerate(accounts):
        if acc["handle"] == handle:
            accounts[i].update(creds)
            print(f"Updated existing account @{handle}")
            break
    else:
        account = {"handle": handle, "enabled": True, **creds}
        accounts.append(account)
        print(f"Added new account @{handle}")

    config["platforms"]["x"]["enabled"] = True

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    print(f"Total X accounts: {len(accounts)}")
    for acc in accounts:
        status = "enabled" if acc.get("enabled", True) else "disabled"
        auth = "cookies" if acc.get("auth_token") else "login" if acc.get("username") else "none"
        print(f"  @{acc['handle']} ({status}, {auth})")


if __name__ == "__main__":
    main()
