"""Pin physical constants to their PDG values.

Other tests compare against these constants, so a typo here would pass
them silently. These literal values are the independent check.
"""

from pi0resolve import constants
from pi0resolve.transport import PAIR_FACTOR


def test_pi0_constants_match_pdg():
    assert constants.PI0_MASS == 0.1349768        # GeV, 134.9768 MeV
    assert constants.PI0_BR_GAMMA_GAMMA == 0.98823
    assert constants.PI0_BR_DALITZ == 0.01174


def test_pair_production_factor():
    assert PAIR_FACTOR == 7.0 / 9.0
