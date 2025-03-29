#!/bin/bash
uv export --frozen > requirements.txt
uv pip install -r requirements.txt --target . --python-platform x86_64-manylinux_2_17
rm requirements.txt