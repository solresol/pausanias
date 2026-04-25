# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Run Commands
- Run a script: `python script_name.py`
- Run with limited processing: `python script_name.py --stop=N` (process N items)
- Run daily analysis: `./cronscript.sh`

## Code Style Guidelines
- Use snake_case for function and variable names
- Keep functions focused on a single task with descriptive names
- Place standard library imports first, followed by third-party packages
- Use docstrings for function documentation
- Maintain compatibility with Python 3.11+
- Follow existing error handling patterns with explicit error messages

## Dependencies
- Use `uv` for dependency management
- Core dependencies: matplotlib, networkx, numpy, openai, pandas, scikit-learn, tqdm

## Project Structure
- Data flow: import → extract → analyze → visualize → generate website
- Database: PostgreSQL. The live database is on `raksasa` (`dbname=pausanias`,
  user `gregb`); the local default `dbname=pausanias` only works if a local
  server is running. For local scripts, use an SSH tunnel to raksasa's Postgres
  socket, for example `ssh -N -L 6543:/var/run/postgresql/.s.PGSQL.5432
  raksasa`, then run with `--database-url "host=127.0.0.1 port=6543
  dbname=pausanias user=gregb"`.
- Network analysis outputs feed into website generation

## Testing
- Add tests in a "tests" directory if implementing new features
- Test with limited data using the --stop parameter
