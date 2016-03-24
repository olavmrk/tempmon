tempmon.py
==========

This is a Python 3 script for polling 1-wire temperature sensors and reporting the data to InfluxDB.

Installation
------------

This is easiest to install in a virtualenv:

```
virtualenv --python=python3 .virtualenv
./.virtualenv/bin/pip install -r requirements.txt
```

Then you must create a `settings.py`-file with configuration:

```
cp settings.py.example settings.py
nano settings.py
```

Once the configuration is in place, the script can be launched:

```
./.virtualenv/bin/python tempmon.py
```
