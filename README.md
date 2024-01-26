# myldapsync - adopted for MySQL fork of pgldapsync by EnterpriseDB Corporation (work in progress)
# pgldapsync - https://github.com/EnterpriseDB/pgldapsync

This Python module allows you to synchronise MySQL users
with users in an LDAP directory.

*myldapsync is supported on Python 3.7 or later.*

In order to use it, you will need to create a _config.ini_ 
file containing the site-specific configuration you require. 
See _config.ini.example_ for a complete list of all the 
available configuration options. This file should be copied to
create your own configuration.

Once configured, simply run myldapsync like so:

    python3 myldapsync.py /path/to/config.ini
    
In order to test the configuration (and dump the SQL that would
be executed to stdout), run it like this:

    python3 myldapsync.py --dry-run /path/to/config.ini

## Creating a virtual environment for dev/test

    python3 -m venv /path/to/myldapsync
    source /path/to/myldapsync/bin/activate.sh
    pip install -r requirements.txt
    
Adapt the first command as required for your environment/Python
version.

## Creating a package

To create a package (wheel), run the following in your virtual 
environment:

    python3 setup.py sdist bdist_wheel --universal
