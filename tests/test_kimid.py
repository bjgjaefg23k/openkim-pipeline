""" Test some of the functionality of the kimid module """

from test_config import *

import kimid

KID = "NAME__TE_012345678901_000"


def test_parse_full():
    """ Test a full kimid parse """
    KID = "NAME__TE_012345678901_000"
    header, leader, pk, version = kimid.parse_kimid(KID)
    assert header == "NAME"
    assert leader == "TE"
    assert pk == "012345678901"
    assert version == 0


def test_parse_without_name():
    """ Test a kimid parse without a name """
    KID = "TE_012345678901_000"
    header, leader, pk, version = kimid.parse_kimid(KID)
    assert header == None
    assert leader == "TE"
    assert pk == "012345678901"
    assert version == 0
