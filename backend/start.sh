#!/bin/bash
cd "$(dirname "$0")"

echo "Starting zizi AI Backend..."
DASHSCOPE_API_KEY="sk-cc5a6489bd094ed1be108863c8c8f50e" /Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
