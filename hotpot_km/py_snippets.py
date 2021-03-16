python_update_cwd_code = """
import os;
os.chdir({cwd!r});
del os;
"""

python_update_env_code = """
import os;
for key, value in {env!r}.items():
    os.environ[key] = value;
del key
del value
del os;
"""

python_init_import_code = """
import importlib
for name in {modules!r}:
    importlib.import_module(name)
    del name
del importlib
"""
