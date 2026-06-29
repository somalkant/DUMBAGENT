#!/bin/bash
cd ~/DUMBAGENT
source venv/bin/activate
exec python run_live.py "$@"
