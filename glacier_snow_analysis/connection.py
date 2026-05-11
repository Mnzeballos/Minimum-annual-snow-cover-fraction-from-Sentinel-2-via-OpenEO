"""
connection.py
-------------
Handles OpenEO authentication and connection setup.
"""

import openeo

OPENEO_URL = "https://openeo.dataspace.copernicus.eu/"


def connect_openeo(url: str = OPENEO_URL) -> openeo.Connection:
    """
    Connect and authenticate to an OpenEO backend.

    Parameters
    ----------
    url : str
        OpenEO backend URL. Defaults to Copernicus Dataspace.

    Returns
    -------
    openeo.Connection
        An authenticated OpenEO connection.
    """
    conn = openeo.connect(url)
    conn.authenticate_oidc()
    return conn
