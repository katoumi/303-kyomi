"""
Kyomi entrypoint wrapper for hosts expecting main.py
"""
import runpy

if __name__ == "__main__":
    runpy.run_module("bot", run_name="__main__")
