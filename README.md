# siri-score
Because every development team has a weak link...

SIRI: Should I Rewrite It?

Run siri.py and provide a path to analyze.

> siri.py -r my-project

The SIRI script will provide a score based on how much code has been written by individuals identified in the siri_authors dictionary. The script is currently configured to analyze iOS source code based on the code_files and resource_files lists.

Ideally, the script would use a siri.config file to pull in the list of authors and project file patterns.

This script requires gitpython to run. Install gitpython into your Python environment using:

> pip install gitpython

This may require elevated privileges through sudo.
