# Onyx Developer Tools (ods)

A CLI tool providing developer utilities for working on [Onyx](https://onyx.app).

## Installation

```bash
# Install via pip (includes Go binary)
pip install onyx-devtools

# Or install from source
cd tools/ods
pip install -e .
```

## Commands

### OpenAPI Schema & Client Generation

Generate OpenAPI schema and Python client for integration testing:

```bash
# Generate OpenAPI schema
ods openapi schema

# Generate Python client from schema
ods openapi client

# Generate both schema and client
ods openapi all

# Custom output paths
ods openapi schema -o ./api.json
ods openapi client -o ./my_client
```

### Database Operations

Manage local development databases:

```bash
# Run database migrations
ods db migrate

# Dump database to file
ods db dump

# Restore database from file
ods db restore

# Drop database
ods db drop
```

### Cherry-Pick Tool

Assist with cherry-picking commits across branches:

```bash
ods cherry-pick <commit-sha>
```

### Check Lazy Imports

Validate lazy import patterns in the codebase:

```bash
ods check-lazy-imports
```

## Development

The tool is written in Go and distributed as a Python package with pre-built binaries.

### Building from Source

```bash
cd tools/ods

# Build Go binary
go build -o ods .

# Run directly
./ods --help
```

### Project Structure

```
tools/ods/
├── main.go              # Entry point
├── cmd/                 # Command implementations
│   ├── root.go          # Root command
│   ├── openapi.go       # OpenAPI commands
│   ├── db.go            # Database parent command
│   ├── db_migrate.go    # Migration command
│   ├── db_dump.go       # Dump command
│   ├── db_restore.go    # Restore command
│   ├── db_drop.go       # Drop command
│   └── cherry-pick.go   # Cherry-pick command
├── internal/            # Internal packages
├── go.mod               # Go dependencies
├── pyproject.toml       # Python package config
└── hatch_build.py       # Build hook for Go binary
```

## Debug Mode

Enable debug logging:

```bash
ods --debug <command>
```

## Version

```bash
ods --version
```
