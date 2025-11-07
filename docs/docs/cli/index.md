# virapi CLI

This document describes how to use the virapi Command Line Interface (CLI) script to start and manage your virapi ASGI applications using Uvicorn.

## 1. Overview

The virapi CLI is designed to simplify the process of launching your application in either development or production mode, automatically handling Uvicorn configuration like host binding, port, and code hot-reloading.

The script expects your virapi application instance to be named app within the specified file (e.g., ```app = virapi()```).

## 2. Prerequisites

This CLI requires the Uvicorn library to be installed in your Python environment. If it's not installed, the script will exit with a fatal error.

```shell
pip install uvicorn
```

## 3. Core Commands

The CLI supports two main subcommands: dev for development and run for production.

General Syntax

```shell
virapi <command> [options]
```

### 3.1. dev (Development Mode)

Use the dev command for local development. It automatically enables file watching and auto-reload.

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| --app-file | str | app.py | Path to the file containing the virapi instance. |
| --port | int | 8000 | The port the server will listen on. |
| --reload | bool | True | Enable/disable auto-reload on code changes. |

#### Example Usage (Development)

To run your application defined in main.py on port 8080 with auto-reload:

```shell
virapi dev --app-file main.py --port 8080
```

- Host Binding: Automatically binds to 127.0.0.1 (localhost).
- Reload: Enabled by default. It watches the directory of your app file for changes.

### 3.2. run (Production Mode)

Use the run command for deploying your application. It disables auto-reload and binds to a public host.

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| --app-file | str | app.py | Path to the file containing the virapi instance. |
| --port | int | 8000 | The port the server will listen on. |

Example Usage (Production)

To run your application defined in app.py on port 8000 for public access:

```shell
virapi run
```

- Host Binding: Automatically binds to 0.0.0.0 (accessible from outside the local machine/container).
- Reload: Explicitly disabled (False).

## 4. How the CLI Works (Internal Logic)

The script performs two critical steps to ensure Uvicorn can find and run your virapi application:

- Application String Formatting: The find_app_string function takes the provided ```--app-file``` (e.g., main.py) and converts it to the Uvicorn-required format: ```module:app_object``` (e.g., ```main:app```). This tells Uvicorn to look for an object named app inside the main module.

- System Path Injection: The script ensures the directory containing your application file is added to the sys.path. This is vital for Uvicorn to correctly import the module containing your app without running into ```ModuleNotFoundError``` errors, especially when running the CLI from a different directory than the app itself.