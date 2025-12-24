#!/usr/bin/env python3
"""Wrapper to run Codex autonomous coding agent with GPT-5.2-pro"""
import subprocess
import sys
import os

env = {"CODEX_MODEL": "gpt-5.2"}
cmd = ["python3", "/Users/home/.codex/scripts/autonomous.py"] + sys.argv[1:]
subprocess.run(cmd, env={**os.environ, **env})
