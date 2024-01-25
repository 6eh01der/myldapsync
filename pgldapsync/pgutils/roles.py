###############################################################################
#
# myldapsync - adopted for MySQL fork of pgldapsync by EnterpriseDB Corporation
#
# Synchronise MySQL users with users in an LDAP directory.
#
###############################################################################

"""MySQL role functions."""

import sys

import ast
import mysql.connector


def get_my_users(conn):
    """Get a list of user from the MySQL server.

    Args:
        conn (connection): The MySQL connection object
    Returns:
        str[]: A list of user names
    """
    cur = conn.cursor()

    try:
        cur.execute("SELECT user AS role_name FROM mysql.user WHERE account_locked='N' AND password_expired='N' AND authentication_string IS NOT NULL;")
        rows = cur.fetchall()
    except mysql.connector.Error as exception:
        sys.stderr.write("Error retrieving MySQL users: %s\n" %
                         exception)
        return None

    roles = []

    for row in rows:
        roles.append(row[0])

    cur.close()

    return roles


def get_filtered_my_users(config, conn):
    """Get a filtered list of users from the MySQL server, having
    removed users to be ignored.

    Args:
        config (ConfigParser): The application configuration
        conn (connection): The MySQL connection object
    Returns:
        str[]: A filtered list of users
    """
    roles = get_my_users(conn)
    if roles is None:
        return None

    # Remove ignored roles
    for role in config.get('mysql', 'ignore_users').split(','):
        try:
            roles.remove(role)
        except ValueError:
            pass

    return roles


def get_user_privileges(config, admin):
    """Generate a list of user privileges to use when creating users

    Args:
        config (ConfigParser): The application configuration
        admin (bool): Should the user be a superuser regardless of the config?
    Returns:
        str: A SQL snippet listing the role attributes
    """
    privilege_list = ''
    if config.getboolean('general', 'role_privilege_all') or admin:
        privilege_list = privilege_list + 'ALL'

    if config.getboolean('general', 'role_privilege_create'):
        privilege_list = privilege_list + ' CREATE'

    if config.getboolean('general', 'role_privilege_create_role'):
        privilege_list = privilege_list + ' CREATE ROLE'

    return privilege_list


def get_user_grants(config, role, with_admin=False):
    """Get a SQL string to GRANT membership to the configured roles when
    creating a new user.

    Args:
        config (ConfigParser): The application configuration
        role (str): The role name to be granted additional roles
        with_admin (bool): Generate a list of roles that will have the WITH
            ADMIN OPTION specified, if True
    Returns:
        str: A SQL snippet listing the role GRANT statements required
    """
    roles = ''
    sql = ''

    if with_admin:
        roles_to_grant = config.get('general',
                                    'roles_to_grant_with_admin').split(',')
    else:
        roles_to_grant = config.get('general', 'roles_to_grant').split(',')

    for role_to_grant in roles_to_grant:
        roles = roles + '"' + role_to_grant + '", '

    if roles.endswith(', '):
        roles = roles[:-2]

    if roles != '':
        sql = 'GRANT %s ON *.* TO "%s"' % (roles, role)

        if with_admin:
            sql = sql + " WITH ADMIN OPTION"

        sql = sql + ';'

    return sql

def get_create_users(ldap_users, my_users):
    """Get a filtered list of users to create.

    Args:
        ldap_users (str[]): A list of users in LDAP
        my_users (str[]): A list of users in MySQL

    Returns:
        str[]: A list of roles that exist in LDAP but not in MySQL
    """
    roles = []

    for user in ldap_users:
        if user not in my_users:
            roles.append(user)

    return roles


def get_drop_users(ldap_users, my_users):
    """Get a filtered list of users to drop.

    Args:
        ldap_users (str[]): A list of users in LDAP
        my_users (str[]): A list of roles in MySQL

    Returns:
        str[]: A list of roles that exist in MySQL but not in LDAP
    """
    roles = []

    for role in my_users:
        if role not in ldap_users:
            roles.append(role)

    return roles
