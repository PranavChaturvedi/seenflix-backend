/bin/bash uv export --frozen > requirements.txt
/bin/bash uv pip install -r requirements.txt --target . --python-platform x86_64-manylinux_2_17
/bin/bash rm requirements.txt