import argparse
import sys
import os
from typing import Optional, List

# =================================================================
# --- Uvicorn Setup: REQUIERE 'pip install uvicorn' ---
try:
    import uvicorn
except ImportError:
    print("FATAL ERROR: 'uvicorn' library is not installed")
    print("Please install it using: pip install uvicorn")
    sys.exit(1)
# =================================================================


def find_app_string(file_path: str = "app.py") -> str:
    """
    Formats the file path to Uvicorn convention: 'module:app_object'.

    Assumes that application object is named 'app' inside the file.
    Args:
        file_path: Path to the file containing the Vira instance.
    """
    # Usamos os.path.basename para obtener solo el nombre del módulo sin ruta
    module_name = os.path.basename(file_path).replace(".py", "")
    return f"{module_name}:app"


def main():
    """Main entry point for the Vira CLI interface."""
    parser = argparse.ArgumentParser(
        description="Vira Framework Command Line Interface for running ASGI applications.",
        epilog="Example: python vira_cli.py dev --app-file main.py"
    )
    
    subparsers = parser.add_subparsers(dest='command', required=True)

    # --- Command 'dev' (Development Mode) ---
    dev_parser = subparsers.add_parser(
        'dev',
        help='Run the application in development mode with auto-reload (Uvicorn).',
        description='Binds to 127.0.0.1 (localhost) and enables auto-reload.'
    )
    dev_parser.add_argument(
        '--app-file',
        type=str,
        default='app.py',
        help='Path to the file containing the Vira instance (e.g., main.py).'
    )
    dev_parser.add_argument(
        '--port', 
        type=int, 
        default=8000, 
        help='The port to listen on.'
    )
    dev_parser.add_argument(
        '--reload', 
        type=bool, 
        default=True, 
        help='Enable auto-reload on code changes.'
    )

    # --- Command 'run' (Production Mode) ---
    run_parser = subparsers.add_parser(
        'run',
        help='Run the application in production mode.',
        description='Binds to 0.0.0.0 (public) and disables auto-reload.'
    )
    run_parser.add_argument(
        '--app-file',
        type=str,
        default='app.py',
        help='Path to the file containing the Vira instance (e.g., main.py).'
    )
    run_parser.add_argument(
        '--port', 
        type=int, 
        default=8000, 
        help='The port to listen on.'
    )

    # --- Parse arguments ---
    args = parser.parse_args()
    
    # -------------------------------------------------------------
    # Safe variable extraction to avoid UnboundLocalError
    # -------------------------------------------------------------
    app_file_name: str = args.app_file
    port: int = args.port
    command: str = args.command
    reload: bool = args.reload if hasattr(args, 'reload') else False
    
    # 1. Obtain absolute path of the app file
    app_file_path = os.path.abspath(app_file_name)
    app_dir = os.path.dirname(app_file_path)

    # Inject the application directory into the sys.path of the current process.
    # This ensures that the Uvicorn subprocess inherits the correct import path
    # and resolves the 'Could not import module' error.
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    # 2. Prepare Uvicorn
    app_string = find_app_string(app_file_name)
    
    if command == 'dev':
        host = '127.0.0.1'
        reload = reload
        # Specify the directories for Uvicorn to watch for reload
        reload_dirs: Optional[List[str]] = [app_dir]
        log_level = "info"
    elif command == 'run':
        host = '0.0.0.0'
        reload = False
        reload_dirs = None
        log_level = "warning"
    else:
        parser.print_help()
        sys.exit(1)

    # 3. Execute Uvicorn
    print(f"Vira CLI: Running in {command.upper()} mode")
    print(f"Host: http://{host}:{port}")
    print(f"App: {app_string}")
    # print("-" * 30)
    
    try:
        uvicorn.run(
            app_string, 
            host=host, 
            port=port, 
            reload=reload,
            reload_dirs=reload_dirs,
            log_level=log_level,
            log_config=None
        )
    except Exception as e:
        print(f"\nFATAL ERROR: The server failed to start or find the application '{app_file_name}'.")
        print(f"Ensure that the file contains 'app = Vira()' and that all dependencies are installed.")
        print(f"Error details: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()