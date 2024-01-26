###############################################################################
#
# myldapsync - adopted for MySQL fork of pgldapsync by EnterpriseDB Corporation
#
# Synchronise MySQL users with users in an LDAP directory.
#
###############################################################################

"""config file functions."""

import sys

def get_ldap_conf(config, admin):
    """Get base_dn and search_filter from config file.

    Args:
        config (ConfigParser): The application configuration
        admin (bool): Return admin search filter?
    Returns:
        tuple(): base_dn string and search_filter string
    """

    if admin:
        base_dn = config.get('ldap', 'admin_base_dn')
        search_filter = config.get('ldap', 'admin_filter_string')
    else:
        base_dn = config.get('ldap', 'base_dn')
        search_filter = config.get('ldap', 'filter_string')

    return base_dn, search_filter