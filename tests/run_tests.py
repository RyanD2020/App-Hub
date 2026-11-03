# Databricks notebook source
# MAGIC %md
# MAGIC # App hub tests
# MAGIC Open this notebook from the App hub Git folder (on the branch you want to test) and click **Run all**.
# MAGIC It installs the app's pinned packages plus pytest on serverless compute, then runs everything in `tests/`.
# MAGIC The last cell fails if any test fails, so a scheduled run of this notebook can alert on failures too.

# COMMAND ----------

# MAGIC %pip install -q -r ../requirements.txt pytest==9.2.0

# COMMAND ----------

dbutils.library.restartPython()  # noqa: F821 (dbutils exists in Databricks notebooks)

# COMMAND ----------

import os
import sys

import pytest

here = os.getcwd()  # a Git-folder notebook starts in its own folder
root = os.path.dirname(here) if os.path.basename(here) == "tests" else here
assert os.path.exists(os.path.join(root, "app.py")), f"Can't find the App hub folder from {here}"
os.chdir(root)
sys.dont_write_bytecode = True  # keep __pycache__ out of the Git folder

code = pytest.main(["-v", "-p", "no:cacheprovider", "tests"])
if code != 0:
    raise Exception(f"pytest failed (exit code {int(code)}). The failing tests are listed above.")
print("All App hub tests passed.")
