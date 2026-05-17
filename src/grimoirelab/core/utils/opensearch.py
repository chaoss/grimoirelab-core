# -*- coding: utf-8 -*-
#
# Copyright (C) GrimoireLab Contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import warnings

import certifi
import urllib3
from opensearchpy import OpenSearch
from django.conf import settings
from urllib3.util import create_urllib3_context


def get_opensearch_client():
    url = settings.GRIMOIRELAB_ARCHIVIST["STORAGE_URL"]
    username = settings.GRIMOIRELAB_ARCHIVIST["STORAGE_USERNAME"]
    password = settings.GRIMOIRELAB_ARCHIVIST["STORAGE_PASSWORD"]
    verify_certs = settings.GRIMOIRELAB_ARCHIVIST["STORAGE_VERIFY_CERT"]

    context = None
    if verify_certs:
        # Use certificates from the local system and certifi
        context = create_urllib3_context()
        context.load_default_certs()
        context.load_verify_locations(certifi.where())
    else:
        # Ignore SSL warnings if not verifying certificates
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        warnings.filterwarnings("ignore", message=".*verify_certs.*")

    auth = (username, password) if username and password else None

    client = OpenSearch(
        hosts=[url],
        http_auth=auth,
        http_compress=True,
        verify_certs=verify_certs,
        ssl_context=context,
        ssl_show_warn=False,
        max_retries=3,
        retry_on_timeout=True,
    )

    return client
