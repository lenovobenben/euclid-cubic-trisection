"""Precision workaround for SageMath 10.7's exact algebraic-number backend."""

from sage.env import SAGE_VERSION
from sage.rings.qqbar import AlgebraicGenerator


def _pari_field_with_precision(self):
    if self.is_trivial():
        raise ValueError("No PARI field attached to trivial generator")
    if self._pari_field is None:
        polynomial = self._field.polynomial()
        coefficient_bits = max(coefficient.height().nbits() for coefficient in polynomial)
        precision = max(64, 2 * polynomial.degree() * coefficient_bits)
        self._pari_field = self._field.pari_polynomial("y").nfinit(1, precision=precision)
        # Both Sage caches must use the same high-precision integral number field.
        self._field._pari_nf = self._pari_field[0]
    return self._pari_field


# Sage 10.7 initializes these PARI fields at 64 bits. Large coefficients can
# then make exact field unions fail with "impossible inverse ... 0.E...".
# Precision changes the auxiliary real embeddings. Arithmetic stays exact.
if SAGE_VERSION == "10.7":
    AlgebraicGenerator.pari_field = _pari_field_with_precision
