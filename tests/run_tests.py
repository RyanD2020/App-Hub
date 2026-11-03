# Databricks notebook source
# MAGIC %md
# MAGIC # App hub tests
# MAGIC Open this notebook from the App hub Git folder (on the branch you want to test) and click **Run all**.
# MAGIC It installs the app's pinned packages plus pytest on serverless compute, then runs everything in `tests/`.
# MAGIC The last cell fails if any test fails, so a scheduled run of this notebook can alert on failures too.
# MAGIC It can be run again in the same session: nothing here changes Python's working folder for the next run.

# COMMAND ----------

import os

# Start from this notebook's own folder (tests/), so the next cell finds ../requirements.txt. A notebook normally starts
# there, but an earlier run in the same session (before this cell existed) could have left Python somewhere else.
try:
    notebook = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()  # noqa: F821
    folder = os.path.dirname(notebook)
    os.chdir(folder if folder.startswith("/Workspace") else "/Workspace" + folder)
except Exception:  # noqa: BLE001  (fall back to the folder Python is in)
    if os.path.basename(os.getcwd()) != "tests" and os.path.isdir("tests"):
        os.chdir("tests")
assert os.path.isfile("../requirements.txt"), f"Can't find the App hub's requirements.txt from {os.getcwd()}"
print("Testing the App hub in", os.path.dirname(os.getcwd()))

# COMMAND ----------

# MAGIC %pip install -q -r ../requirements.txt pytest==9.2.0

# COMMAND ----------

# dbutils exists in Databricks notebooks. Nothing follows the call in this cell, so Databricks doesn't warn.
dbutils.library.restartPython()  # noqa: F821

# COMMAND ----------

import os
import sys

import pytest

here = os.getcwd()  # after the restart, Python is back in this notebook's folder (tests/)
root = os.path.dirname(here) if os.path.basename(here) == "tests" else here
assert os.path.exists(os.path.join(root, "app.py")), f"Can't find the App hub folder from {here}"
sys.dont_write_bytecode = True  # keep __pycache__ out of the Git folder

# The tests find every file from their own location, so Python's working folder is left as it is.
code = pytest.main(["-v", "-p", "no:cacheprovider", os.path.join(root, "tests")])
if code != 0:
    raise Exception(f"pytest failed (exit code {int(code)}). The failing tests are listed above.")
print("All App hub tests passed.")
