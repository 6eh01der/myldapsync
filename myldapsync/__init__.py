###############################################################################
#
# myldapsync - adopted for MySQL fork of pgldapsync by EnterpriseDB Corporation
#
# Synchronise MySQL users with users in an LDAP directory.
#
###############################################################################

"""myldapsync main entry point."""

# FIX THIS!
# pylint: disable=too-many-branches,too-many-locals,too-many-statements

import argparse
import os

import configparser

from myldapsync.ldaputils.connection import connect_ldap_server
from myldapsync.ldaputils.users import *
from myldapsync.myutils.connection import connect_my_server
from myldapsync.myutils.users import *


def read_command_line():
    """Read the command line arguments.

    Returns:
        ArgumentParser: The parsed arguments object
    """
    parser = argparse.ArgumentParser(
        description='Synchronise users and groups from LDAP/AD to MySQL.')
    parser.add_argument("--dry-run", "-d", action='store_true',
                        help="don't apply changes to the database server, "
                             "dump the SQL to stdout instead")
    parser.add_argument("config", metavar="CONFIG_FILE",
                        help="the configuration file to read")

    args = parser.parse_args()

    return args


def read_config(file):
    """Read the config file.

    Args:
        file (str): The config file to read
        my_user (str[]): A list of users in MySQL

    Returns:
        ConfigParser: The config object
    """
    config = configparser.ConfigParser()

    # Read the default config
    defaults = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        'config_default.ini')

    try:
        config.read(defaults)
    except configparser.Error as exception:
        sys.stderr.write(
            "Error reading default configuration file (%s): %s\n" %
            (defaults, exception))
        sys.exit(1)

    try:
        config.read(file)
    except configparser.Error as exception:
        sys.stderr.write(
            "Error reading user configuration file (%s): %s\n" %
            (file, exception))
        sys.exit(1)

    return config


def main():
    """The core structure of the app."""

    # Read the command line options
    args = read_command_line()

    # Read the config file
    config = read_config(args.config)

    # Connect to LDAP and get the users we care about
    ldap_conn = connect_ldap_server(config)
    if ldap_conn is None:
        sys.exit(1)

    ldap_users = get_filtered_ldap_users(config, ldap_conn, False)
    if ldap_users is None:
        sys.exit(1)

    # Get ldap base dn and search filter
    ldap_conf = get_ldap_conf(config, False)
    if ldap_conf is None:
        sys.exit(1)

    # Get the LDAP admin users, if the base DN and filter are configured
    if config.get('ldap', 'admin_base_dn') == '' or \
            config.get('ldap', 'admin_filter_string') == '':
        ldap_admin_users = []
    else:
        ldap_admin_users = get_ldap_users(config, ldap_conn, True)
    if ldap_admin_users is None:
        sys.exit(1)

    # Connect to MySQL and get the users we care about
    my_conn = connect_my_server(config.get('mysql', 'server_connstr'))
    if my_conn is None:
        sys.exit(1)

    my_users = get_filtered_my_users(config, my_conn)
    if my_users is None:
        sys.exit(1)

    # Compare the LDAP and MySQL users and get the lists of users
    # to add and drop.
    users_to_create = get_create_users(ldap_users, my_users)
    users_to_drop = get_drop_lusers(ldap_users, my_users)

    # Create/drop users if required
    have_work = ((config.getboolean('general',
                                    'add_ldap_users_to_mysql') and
                  len(users_to_create) > 0) or
                 (config.getboolean('general',
                                    'remove_users_from_mysql') and
                  len(users_to_drop) > 0))

    # Initialise the counters for operations/errors
    users_added = 0
    users_dropped = 0
    users_add_errors = 0
    users_drop_errors = 0

    # Warn the user we're in dry run mode
    if args.dry_run:
        print("-- This is an LDAP sync dry run.")
        print("-- The commands below can be manually executed if required.")

    cur = None
    if have_work:

        # Begin the transaction
        if args.dry_run:
            print("BEGIN;")
        else:
            cur = my_conn.cursor()
            cur.execute("BEGIN;")

    # If we need to add users to MySQL, then do so
    if config.getboolean('general', 'add_ldap_users_to_mysql'):

        # For each user, get the required attributes and SQL snippets
        for user in users_to_create:
            user_name = user.replace('\'', '\\\'')
            user_grants = get_user_grants(config, user_name)
            user_admin_grants = get_user_grants(config, user_name, True)
            privilege_list = get_user_attributes(config,
                                                 (user in ldap_admin_users))

            if args.dry_run:

                # It's a dry run, so just print the output
                print('CREATE USER "%s" IDENTIFIED WITH authentication_ldap_simple; GRANT "%s" ON *.* TO "%s"; GRANT "%s","%s" TO "%s";' %
                        (user_name, privilege_list, user_name, user_grants, user_admin_grants, user_name))
                print(privilege_list)
                print(user_grants)
                print(user_admin_grants)
            else:

                # This is a live run, so directly execute the SQL generated.
                # For each statement, create a savepoint so we can rollback
                # to it if there's an error. That allows us to fail only
                # a single user rather than all of them.
                try:
                    # We can't use a real parameterised query here as we're
                    # working with an object, not data.
                    cur.execute('SAVEPOINT cr; CREATE USER "%s" IDENTIFIED WITH authentication_ldap_simple; GRANT "%s" ON *.* TO "%s"; GRANT "%s","%s" TO "%s";' %
                                   (user_name, privilege_list, user_name, user_grants, user_admin_grants, user_name))
                    users_added = users_added + 1
                except mysql.connector.Error as exception:
                    sys.stderr.write("Error creating user %s: %s" % (user,
                                                                     exception))
                    users_add_errors = users_add_errors + 1
                    cur.execute('ROLLBACK TO SAVEPOINT cr;')

    # If we need to drop users from MySQL, then do so
    if config.getboolean('general', 'remove_users_from_mysql'):

        # For each user to drop, just run the DROP statement
        for user in users_to_drop:

            if args.dry_run:

                # It's a dry run, so just print the output
                print('DROP USER "%s";' % user.replace('\'', '\\\''))
            else:

                # This is a live run, so directly execute the SQL generated.
                # For each statement, create a savepoint so we can rollback
                # to it if there's an error. That allows us to fail only
                # a single user rather than all of them.
                try:
                    # We can't use a real parameterised query here as we're
                    # working with an object, not data.
                    cur.execute('SAVEPOINT dr; DROP USER "%s";' %
                                user.replace('\'', '\\\''))
                    users_dropped = users_dropped + 1
                except mysql.connector.Error as exception:
                    sys.stderr.write("Error dropping user %s: %s" % (user,
                                                                     exception))
                    users_drop_errors = users_drop_errors + 1
                    cur.execute('ROLLBACK TO SAVEPOINT dr;')

    if have_work:

        # Commit the transaction
        if args.dry_run:
            print("COMMIT;")
        else:
            cur.execute("COMMIT;")
            cur.close()

            # Print the summary of work completed
            print("Users added to MySQL:     %d" % users_added)
            print("Users dropped from MySQL: %d" % users_dropped)
            if users_add_errors > 0:
                print("Errors adding users:         %d" %
                      users_add_errors)
            if users_drop_errors > 0:
                print("Errors dropping users:       %d" %
                      users_drop_errors)
    else:
        print("No users were added or dropped.")