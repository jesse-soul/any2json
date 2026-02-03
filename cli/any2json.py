#!/usr/bin/env python3
"""
any2json CLI — TUI client for any2json API
"""

import os
import sys
import json
import httpx
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich import box
import pyotp
import qrcode
from io import StringIO

# Config
API_BASE = os.environ.get("ANY2JSON_API", "https://any2json.ai/api")
CONFIG_DIR = Path.home() / ".any2json"
CONFIG_FILE = CONFIG_DIR / "config.json"

console = Console()


def load_config() -> dict:
    """Load saved config."""
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config: dict):
    """Save config to disk."""
    CONFIG_DIR.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def api_request(method: str, endpoint: str, data: dict = None, token: str = None) -> dict:
    """Make API request."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        with httpx.Client(timeout=30) as client:
            if method == "GET":
                r = client.get(f"{API_BASE}{endpoint}", headers=headers)
            else:
                r = client.post(f"{API_BASE}{endpoint}", json=data, headers=headers)
            return r.json()
    except Exception as e:
        return {"error": str(e)}


def show_header():
    """Display header."""
    console.print()
    console.print(Panel(
        Text("any2json", style="bold magenta", justify="center"),
        subtitle="Media → JSON with token control",
        box=box.ROUNDED,
        border_style="bright_blue"
    ))
    console.print()


def show_main_menu(config: dict) -> str:
    """Show main menu."""
    console.print("[bold cyan]━━━ Main Menu ━━━[/bold cyan]\n")
    
    if config.get("token"):
        console.print("  [1] 🔄 Convert media")
        console.print("  [2] 💰 Check balance")
        console.print("  [3] 💳 Add credits")
        console.print("  [4] 🔑 Show API key")
        console.print("  [5] ⚙️  Account settings")
        console.print("  [6] 🚪 Logout")
        console.print("  [0] ❌ Exit")
    else:
        console.print("  [1] 📝 Create account")
        console.print("  [2] 🔐 Login")
        console.print("  [0] ❌ Exit")
    
    console.print()
    return Prompt.ask("Select", choices=["0","1","2","3","4","5","6"] if config.get("token") else ["0","1","2"])


def create_account() -> dict:
    """Create new account flow."""
    console.print("\n[bold green]━━━ Create Account ━━━[/bold green]\n")
    
    email = Prompt.ask("Email")
    password = Prompt.ask("Password", password=True)
    password2 = Prompt.ask("Confirm password", password=True)
    
    if password != password2:
        console.print("[red]Passwords don't match![/red]")
        return {}
    
    console.print("\n[dim]Creating account...[/dim]")
    result = api_request("POST", "/auth/register", {
        "email": email,
        "password": password
    })
    
    if result.get("error"):
        console.print(f"[red]Error: {result['error']}[/red]")
        return {}
    
    console.print("[green]✓ Account created![/green]")
    console.print(f"[dim]Your API key: {result.get('api_key', 'N/A')}[/dim]")
    
    return {
        "email": email,
        "token": result.get("token"),
        "api_key": result.get("api_key")
    }


def login() -> dict:
    """Login flow."""
    console.print("\n[bold blue]━━━ Login ━━━[/bold blue]\n")
    
    email = Prompt.ask("Email")
    password = Prompt.ask("Password", password=True)
    
    console.print("\n[dim]Logging in...[/dim]")
    result = api_request("POST", "/auth/login", {
        "email": email,
        "password": password
    })
    
    if result.get("requires_2fa"):
        code = Prompt.ask("2FA Code")
        result = api_request("POST", "/auth/login", {
            "email": email,
            "password": password,
            "totp_code": code
        })
    
    if result.get("error"):
        console.print(f"[red]Error: {result['error']}[/red]")
        return {}
    
    console.print("[green]✓ Logged in![/green]")
    
    return {
        "email": email,
        "token": result.get("token"),
        "api_key": result.get("api_key")
    }


def check_balance(token: str):
    """Show balance."""
    console.print("\n[bold yellow]━━━ Balance ━━━[/bold yellow]\n")
    
    result = api_request("GET", "/account/balance", token=token)
    
    if result.get("error"):
        console.print(f"[red]Error: {result['error']}[/red]")
        return
    
    table = Table(box=box.ROUNDED)
    table.add_column("Credits", style="green")
    table.add_column("Used", style="yellow")
    table.add_column("Tier", style="cyan")
    
    table.add_row(
        f"${result.get('balance', 0):.2f}",
        f"${result.get('used', 0):.2f}",
        result.get('tier', 'free')
    )
    
    console.print(table)


def add_credits(token: str):
    """Add credits flow."""
    console.print("\n[bold green]━━━ Add Credits ━━━[/bold green]\n")
    
    console.print("Payment methods:")
    console.print("  [1] USDT (TRC-20)")
    console.print("  [2] USDT (ERC-20)")
    console.print("  [3] DAI (Ethereum)")
    console.print("  [4] xDAI (Gnosis)")
    console.print()
    
    choice = Prompt.ask("Select", choices=["1","2","3","4"])
    
    networks = {
        "1": "trc20",
        "2": "erc20", 
        "3": "dai",
        "4": "xdai"
    }
    
    result = api_request("POST", "/payments/get-address", {
        "network": networks[choice]
    }, token=token)
    
    if result.get("error"):
        console.print(f"[red]Error: {result['error']}[/red]")
        return
    
    address = result.get("address", "")
    network_name = result.get("network_name", "")
    
    console.print()
    console.print(Panel(
        f"[bold]{address}[/bold]",
        title=f"Send {network_name} to:",
        border_style="green"
    ))
    console.print()
    console.print("[dim]• Minimum: $5")
    console.print("• Credits added automatically after 1 confirmation")
    console.print("• This address is unique to your account[/dim]")


def show_api_key(config: dict):
    """Show API key."""
    console.print("\n[bold cyan]━━━ API Key ━━━[/bold cyan]\n")
    
    api_key = config.get("api_key", "Not available")
    
    console.print(Panel(
        f"[bold]{api_key}[/bold]",
        title="Your API Key",
        border_style="cyan"
    ))
    console.print()
    console.print("[dim]Usage:[/dim]")
    console.print(f'  curl -H "Authorization: Bearer {api_key[:8]}..." \\')
    console.print(f'    -X POST {API_BASE}/convert \\')
    console.print('    -d \'{"input": "https://...", "max_tokens": 500}\'')


def account_settings(token: str, config: dict):
    """Account settings menu."""
    console.print("\n[bold magenta]━━━ Account Settings ━━━[/bold magenta]\n")
    
    console.print("  [1] 🔒 Setup 2FA")
    console.print("  [2] 🔑 Regenerate API key")
    console.print("  [3] 📧 Change email")
    console.print("  [4] 🔐 Change password")
    console.print("  [0] ← Back")
    console.print()
    
    choice = Prompt.ask("Select", choices=["0","1","2","3","4"])
    
    if choice == "1":
        setup_2fa(token)
    elif choice == "2":
        if Confirm.ask("Regenerate API key? Old key will stop working"):
            result = api_request("POST", "/account/regenerate-key", token=token)
            if result.get("api_key"):
                config["api_key"] = result["api_key"]
                save_config(config)
                console.print(f"[green]New API key: {result['api_key']}[/green]")


def setup_2fa(token: str):
    """Setup 2FA."""
    console.print("\n[bold yellow]━━━ Setup 2FA ━━━[/bold yellow]\n")
    
    result = api_request("POST", "/account/2fa/setup", token=token)
    
    if result.get("error"):
        console.print(f"[red]Error: {result['error']}[/red]")
        return
    
    secret = result.get("secret", "")
    
    # Generate QR code in terminal
    qr = qrcode.QRCode(box_size=1, border=1)
    qr.add_data(result.get("otpauth_url", ""))
    qr.make()
    
    console.print("Scan with your authenticator app:\n")
    qr.print_ascii(out=console.file)
    
    console.print(f"\n[dim]Or enter manually: {secret}[/dim]\n")
    
    # Verify
    code = Prompt.ask("Enter code from app to verify")
    
    verify = api_request("POST", "/account/2fa/verify", {
        "code": code
    }, token=token)
    
    if verify.get("success"):
        console.print("[green]✓ 2FA enabled![/green]")
    else:
        console.print("[red]Invalid code. 2FA not enabled.[/red]")


def convert_media(token: str):
    """Convert media flow."""
    console.print("\n[bold blue]━━━ Convert ━━━[/bold blue]\n")
    
    input_url = Prompt.ask("URL or file path")
    max_tokens = int(Prompt.ask("Max tokens", default="500"))
    
    console.print("\n[dim]Processing...[/dim]")
    
    result = api_request("POST", "/convert", {
        "input": input_url,
        "max_tokens": max_tokens
    }, token=token)
    
    if result.get("error"):
        console.print(f"[red]Error: {result['error']}[/red]")
        return
    
    console.print()
    console.print(Panel(
        json.dumps(result, indent=2),
        title="Result",
        border_style="green"
    ))


def main():
    """Main TUI loop."""
    config = load_config()
    
    while True:
        show_header()
        choice = show_main_menu(config)
        
        if choice == "0":
            console.print("\n[dim]Goodbye![/dim]\n")
            sys.exit(0)
        
        if config.get("token"):
            # Logged in menu
            if choice == "1":
                convert_media(config["token"])
            elif choice == "2":
                check_balance(config["token"])
            elif choice == "3":
                add_credits(config["token"])
            elif choice == "4":
                show_api_key(config)
            elif choice == "5":
                account_settings(config["token"], config)
            elif choice == "6":
                config = {}
                save_config(config)
                console.print("[yellow]Logged out[/yellow]")
        else:
            # Not logged in
            if choice == "1":
                new_config = create_account()
                if new_config:
                    config.update(new_config)
                    save_config(config)
            elif choice == "2":
                new_config = login()
                if new_config:
                    config.update(new_config)
                    save_config(config)
        
        Prompt.ask("\nPress Enter to continue")
        console.clear()


if __name__ == "__main__":
    main()
