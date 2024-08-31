# myldapsync - fork of [pgldapsync](https://github.com/EnterpriseDB/pgldapsync) by [EnterpriseDB Corporation](https://www.enterprisedb.com/) adopted for MySQL and MariaDB

This Python module allows you to synchronise MySQL or MariaDB users
with users in an LDAP directory.

Require MySQL 8 with installed and configured simple or sasl LDAP Authentication Plugin or PAM plugin (pam also supported in MySQL 5.7 and MariaDB).

Percona Server for MySQL:

https://docs.percona.com/percona-server/8.0/ldap-authentication

https://docs.percona.com/percona-server/8.0/pam-plugin.html

MySQL:

https://dev.mysql.com/doc/refman/8.0/en/ldap-pluggable-authentication.html

https://dev.mysql.com/doc/refman/8.0/en/pam-pluggable-authentication.html

MariaDB:

https://mariadb.com/kb/en/authentication-plugin-pam/

*myldapsync is supported on Python 3.8 or later.*

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
    source /path/to/myldapsync/bin/activate
    pip install -r requirements.txt
    
Adapt the first command as required for your environment/Python
version.

## Creating a package

To create a package (wheel), run the following in your virtual 
environment:

    python3 setup.py sdist bdist_wheel
