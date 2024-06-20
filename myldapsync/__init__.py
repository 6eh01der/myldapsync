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

    # MySQL connection dictionary
    connection_string_params = {}

    if (host := config.get('mysql', 'host')) != '':
        connection_string_params = dict(connection_string_params, host=host)

    if (user := config.get('mysql', 'user')) != '':
        connection_string_params = dict(connection_string_params, user=user)

    if (password := config.get('mysql', 'password')) != '':
        connection_string_params = dict(connection_string_params, password=password)

    if (db := config.get('mysql', 'db')) != '':
        connection_string_params = dict(connection_string_params, db=db)

    if (auth_plugin := config.get('mysql', 'auth_plugin')) != '':
        connection_string_params = dict(connection_string_params, auth_plugin=auth_plugin)

    if (ssl_ca := config.get('mysql', 'ssl_ca')) != '':
        connection_string_params = dict(connection_string_params, ssl_ca=ssl_ca)

    if (ssl_cert := config.get('mysql', 'ssl_cert')) != '':
        connection_string_params = dict(connection_string_params, ssl_cert=ssl_cert)

    if (ssl_key := config.get('mysql', 'ssl_key')) != '':
        connection_string_params = dict(connection_string_params, ssl_key=ssl_key)

    if (ssl_verify_identity := config.get('mysql', 'ssl_verify_identity')) != '':
        connection_string_params = dict(connection_string_params, ssl_verify_identity=ssl_verify_identity)

    if (ssl_verify_cert := config.get('mysql', 'ssl_verify_cert')) != '':
        connection_string_params = dict(connection_string_params, ssl_verify_cert=ssl_verify_cert)

    if (use_pure := config.get('mysql', 'use_pure')) != '':
        connection_string_params = dict(connection_string_params, use_pure=use_pure)

    if (SERVICE_NAME := config.get('mysql', 'SERVICE_NAME')) and (LDAP_SERVER_IP := config.get('mysql', 'LDAP_SERVER_IP')) != '':
        connection_string_params = dict(connection_string_params, krb_service_principal=f"{SERVICE_NAME}/{LDAP_SERVER_IP}")

    # Connect to LDAP and get the users we care about
    ldap_conn = connect_ldap_server(config)
    if ldap_conn is None:
        sys.exit(1)

    ldap_users = get_filtered_ldap_users(config, ldap_conn, False)
    if ldap_users is None:
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
    my_conn = mysql.connector.connect(**connection_string_params)
    if my_conn is None:
        sys.exit(1)

    my_users = get_filtered_my_users(config, my_conn)
    if my_users is None:
        sys.exit(1)

    # Compare the LDAP and MySQL users and get the lists of users
    # to add and drop.
    users_to_create = get_create_users(ldap_users, my_users)
    users_to_drop = get_drop_users(ldap_users, my_users)

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
            print("START TRANSACTION;")
        else:
            cur = my_conn.cursor()
            cur.execute("START TRANSACTION;")

    # Set authentication plugin
    auth_plugin = config.get('general', 'auth_plugin')
    if auth_plugin == 'simple':
        identified = 'WITH authentication_ldap_simple'
    elif auth_plugin == 'sasl':
        identified = 'WITH authentication_ldap_sasl'
    elif auth_plugin == 'pam':
        dbms = config.get('general', 'dbms')
        if dbms == 'mysql':
            identified = 'WITH authentication_pam'
        elif dbms == 'psms':
            compat = config.get('general', 'compat')
            if compat:
                identified = 'WITH auth_pam_compat'
            else:
                identified = 'WITH auth_pam'
        elif dbms == 'mariadb':
            identified = 'VIA pam'

    # If we need to add users to MySQL, then do so
    if config.getboolean('general', 'add_ldap_users_to_mysql'):

        # For each user, get the required attributes and SQL snippets
        for user in users_to_create:
            user_name = user.replace('\'', '\\\'')
            user_grants = get_user_grants(config, user_name)
            user_admin_grants = get_user_grants(config, user_name,
                                                 (user in ldap_admin_users))
            privilege_list = get_user_privileges(config, user_name,
                                                 (user in ldap_admin_users))

            if args.dry_run:

                # It's a dry run, so just print the output
                print('CREATE USER "%s" IDENTIFIED %s; %s %s %s' %
                        (user_name, identified, privilege_list, user_grants, user_admin_grants))
            else:

                # This is a live run, so directly execute the SQL generated.
                # For each statement, create a savepoint so we can rollback
                # to it if there's an error. That allows us to fail only
                # a single user rather than all of them.
                try:
                    # We can't use a real parameterised query here as we're
                    # working with an object, not data.
                    cur.execute('CREATE USER "%s" IDENTIFIED %s;' %
                                   (user_name, identified))
                    cur.execute('%s' % privilege_list)
                    cur.execute('%s' % user_grants)
                    cur.execute('%s' % user_admin_grants)
                    users_added = users_added + 1
                except mysql.connector.Error as exception:
                    sys.stderr.write("Error creating user %s: %s" % (user,
                                                                     exception))
                    users_add_errors = users_add_errors + 1
                    cur.execute('ROLLBACK;')

    # If we need to drop users from MySQL, then do so
    if config.getboolean('general', 'remove_users_from_mysql'):

        # For each user to drop, just run the DROP statement
        for user in users_to_drop:

            user_name = user.replace('\'', '\\\'')

            if args.dry_run:

                # It's a dry run, so just print the output
                print('DROP USER "%s";' % user_name)
            else:

                # This is a live run, so directly execute the SQL generated.
                # For each statement, create a savepoint so we can rollback
                # to it if there's an error. That allows us to fail only
                # a single user rather than all of them.
                try:
                    # We can't use a real parameterised query here as we're
                    # working with an object, not data.
                    cur.execute('DROP USER "%s";' % user_name)
                    users_dropped = users_dropped + 1
                except mysql.connector.Error as exception:
                    sys.stderr.write("Error dropping user %s: %s" % (user,
                                                                     exception))
                    users_drop_errors = users_drop_errors + 1
                    cur.execute('ROLLBACK;')

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
