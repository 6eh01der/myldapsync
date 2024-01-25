###############################################################################
#
# myldapsync - adopted for MySQL fork of pgldapsync by EnterpriseDB Corporation
#
# Synchronise MySQL users with users in an LDAP directory.
#
###############################################################################

"""MySQL connection functions."""

import sys

import mysql.connector


def connect_my_server(my_connstr):
    """Setup the connection to the MySQL server.

    Args:
        my_connstr (str): The MySQL connection string

    Returns:
        connection: The mysql-connector-python connection object
    """
    try:
        conn = mysql.connector.connect(my_connstr)
    except mysql.connector.Error as exception:
        sys.stderr.write("Error connecting to the MySQL server: %s\n" %
                         exception)
        return None

    return conn
