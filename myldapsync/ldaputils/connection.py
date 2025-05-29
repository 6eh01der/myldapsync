###############################################################################
#
# myldapsync - adopted for MySQL fork of pgldapsync by EnterpriseDB Corporation
#
# Synchronise MySQL users with users in an LDAP directory.
#
###############################################################################

"""LDAP connection functions."""

# FIX THIS!
# pylint: disable=too-many-branches

import ssl
import sys

from ldap3 import Connection, Server, Tls, SASL, KERBEROS
from ldap3.core.exceptions import LDAPBindError, LDAPSocketOpenError, \
    LDAPStartTLSError, LDAPSASLBindInProgressError, LDAPSASLPrepError, \
    LDAPSASLMechanismNotSupportedError


try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


def connect_ldap_server(config):
    """Setup the connection to the LDAP server.

    Args:
        config (ConfigParser): The application configuration

    Returns:
        ldap3.core.connection.Connection: The LDAP connection object
    """
    # Parse the server URI
    uri = urlparse(config.get('ldap', 'server_uri'))

    # Create the TLS configuration object if required
    tls = None

    if uri.scheme == 'ldaps' or config.getboolean('ldap', 'use_starttls'):

        if (ca_cert_file := config.get('ldap', 'ca_cert_file')) != '':
            pass
        else:
            ca_cert_file = None

        if (cert_file := config.get('ldap', 'cert_file')) != '':
            pass
        else:
            cert_file = None

        if (key_file := config.get('ldap', 'key_file')) != '':
            pass
        else:
            key_file = None

        tls = Tls(
            local_private_key_file=key_file,
            local_certificate_file=cert_file,
            validate=ssl.CERT_REQUIRED, version=ssl.PROTOCOL_TLSv1,
            ca_certs_file=ca_cert_file)

    # Debug
    if config.getboolean('ldap', 'debug'):
        sys.stderr.write(f"TLS/SSL configuration:   {tls}\n")

    # Create the server object
    server = Server(uri.hostname,
                    port=uri.port,
                    tls=tls,
                    use_ssl=uri.scheme == 'ldaps')

    # Debug
    if config.getboolean('ldap', 'debug'):
        sys.stderr.write(f"LDAP server config:      {server}\n")

    # Create the connection
    conn = None
    try:
        if config.get('ldap', 'bind_username') == '' and config.get('ldap', 'use_krb') == '':
            conn = Connection(server, auto_bind=True)
        elif config.get('ldap', 'use_krb') != '':
            if (service_name := config.get('ldap', 'SERVICE_NAME')) and \
                (ldap_server_ip := config.get('ldap', 'LDAP_SERVER_IP')) != '':
                spn = f"{service_name}/{ldap_server_ip}"
                conn = Connection(server, user=spn, authentication=SASL, sasl_mechanism=KERBEROS)
            else:
                conn = Connection(server, authentication=SASL, sasl_mechanism=KERBEROS)
        else:
            conn = Connection(server,
                              config.get('ldap', 'bind_username'),
                              config.get('ldap', 'bind_password'),
                              auto_bind=True)
    except LDAPSocketOpenError as exception:
        sys.stderr.write(f"Error connecting to the LDAP server: {exception}\n")
    except LDAPBindError as exception:
        sys.stderr.write(f"Error binding to the LDAP server: {exception}\n")
    except LDAPSASLBindInProgressError as exception:
        sys.stderr.write(f"SASL bind in progress error: {exception}\n")
    except LDAPSASLPrepError as exception:
        sys.stderr.write(f"SASL prep error: {exception}\n")
    except LDAPSASLMechanismNotSupportedError as exception:
        sys.stderr.write(f"SASL mechanism not supported error: {exception}\n")
    # Debug
    if config.getboolean('ldap', 'debug'):
        sys.stderr.write(f"Initial LDAP connection: {conn}\n")
    # Enable TLS if STARTTLS is configured
    if uri.scheme != 'ldaps' and config.getboolean('ldap', 'use_starttls'):
        try:
            conn.start_tls()
        except LDAPStartTLSError as exception:
            sys.stderr.write(f"Error starting TLS: {exception}\n")
            return None

    # Debug
    if config.getboolean('ldap', 'debug'):
        sys.stderr.write(f"Final LDAP connection:   {conn}\n")

    return conn
