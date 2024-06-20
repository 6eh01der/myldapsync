###############################################################################
#
# myldapsync - adopted for MySQL fork of pgldapsync by EnterpriseDB Corporation
#
# Synchronise MySQL users with users in an LDAP directory.
#
###############################################################################

"""MySQL user functions."""

import sys

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
        cur.execute("SELECT user FROM mysql.user\n"
        "WHERE account_locked='N'\n"
        "AND password_expired='N'\n"
        "AND authentication_string IS NOT NULL;")
        rows = cur.fetchall()
    except mysql.connector.Error as exception:
        sys.stderr.write("Error retrieving MySQL users: %s\n" %
                         exception)
        return None

    users = []

    for row in rows:
        users.append(row[0])

    cur.close()

    return users


def get_filtered_my_users(config, conn):
    """Get a filtered list of users from the MySQL server, having
    removed users to be ignored.

    Args:
        config (ConfigParser): The application configuration
        conn (connection): The MySQL connection object
    Returns:
        str[]: A filtered list of users
    """
    users = get_my_users(conn)
    if users is None:
        return None

    # Remove ignored users
    for user in config.get('mysql', 'ignore_users').split(','):
        try:
            users = [members for members in users if user != members]
        except ValueError:
            pass

    return users


def get_user_privileges(config, user, with_admin=False):
    """Generate a list of user privileges to use when creating users

    Args:
        config (ConfigParser): The application configuration
        user (str): The user name to be granted privileges
        with_admin (bool): Generate a list of privileges that will have the WITH
            GRANT OPTION specified, if True
    Returns:
        str: A SQL snippet listing the user privileges
    """

    privilege_list = ''
    sql = ''

    if (database := config.get('general', 'database')) != '':
        database = '`' + database + '`'
    else:
        database = '*'

    if config.getboolean('general', 'user_privilege_all') or with_admin:
        privilege_list = privilege_list + 'ALL' + ', '
    else:
        if config.getboolean('general', 'user_privilege_create'):
            privilege_list = privilege_list + 'CREATE'+ ', '

        if config.getboolean('general', 'user_privilege_create_role'):
            privilege_list = privilege_list + 'CREATE ROLE'+ ', '

        if config.getboolean('general', 'user_privilege_alter'):
            privilege_list = privilege_list + 'CREATE, INSERT, ALTER'+ ', '

        if config.getboolean('general', 'user_privilege_create_user'):
            privilege_list = privilege_list + 'CREATE USER'+ ', '

        if config.getboolean('general', 'user_privilege_alter_rename'):
            privilege_list = privilege_list + 'CREATE, INSERT, ALTER, DROP'+ ', '

        if config.getboolean('general', 'user_privilege_event'):
            privilege_list = privilege_list + 'EVENT'+ ', '

        if config.getboolean('general', 'user_privilege_execute'):
            privilege_list = privilege_list + 'EXECUTE'+ ', '

        if config.getboolean('general', 'user_privilege_trigger'):
            privilege_list = privilege_list + 'TRIGGER'+ ', '

        if config.getboolean('general', 'user_privilege_insert'):
            privilege_list = privilege_list + 'INSERT'+ ', '

        if config.getboolean('general', 'user_privilege_update'):
            privilege_list = privilege_list + 'UPDATE'+ ', '

        if config.getboolean('general', 'user_privilege_delete'):
            privilege_list = privilege_list + 'DELETE'+ ', '

        if config.getboolean('general', 'user_privilege_drop'):
            privilege_list = privilege_list + 'DROP'+ ', '

    if privilege_list.endswith(', '):
        privilege_list = privilege_list[:-2]

    if privilege_list != '':
        sql = 'GRANT %s ON %s.* TO "%s"' % (privilege_list, database, user)
        if with_admin:
            sql = sql + " WITH GRANT OPTION"
        sql = sql + ';'

    return sql


def get_user_grants(config, user, with_admin=False):
    """Get a SQL string to GRANT membership to the configured roles when
    creating a new user.

    Args:
        config (ConfigParser): The application configuration
        user (str): The user name to be granted roles
        with_admin (bool): Generate a list of roles that will have the WITH
            ADMIN OPTION specified, if True
    Returns:
        str: A SQL snippet listing the user roles
    """
    roles = ''
    sql = ''

    if with_admin:
        roles_to_grant = config.get('general',
                                    'roles_to_grant_with_admin').split(',')
    else:
        roles_to_grant = config.get('general', 'roles_to_grant').split(',')

    if roles_to_grant != ['']:
        for role_to_grant in roles_to_grant:
            roles = roles + '"' + role_to_grant + '", '

    if roles.endswith(', '):
        roles = roles[:-2]

    if roles != '':
        sql = 'GRANT %s TO "%s"' % (roles, user)

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
        str[]: A list of users that exist in LDAP but not in MySQL
    """
    users = []

    for user in ldap_users:
        if user not in my_users:
            users.append(user)

    return users


def get_drop_users(ldap_users, my_users):
    """Get a filtered list of users to drop.

    Args:
        ldap_users (str[]): A list of users in LDAP
        my_users (str[]): A list of users in MySQL

    Returns:
        str[]: A list of users that exist in MySQL but not in LDAP
    """
    users = []

    for user in my_users:
        if user not in ldap_users:
            users.append(user)

    return users
