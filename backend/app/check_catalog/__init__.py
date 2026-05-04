"""Central registry of DQ check templates grouped by DAMA-DMBOK dimensions."""

from typing import Any

from .timeliness.templates import TEMPLATES as TIMELINESS_TEMPLATES
from .validity.templates import TEMPLATES as VALIDITY_TEMPLATES
from .completeness.templates import TEMPLATES as COMPLETENESS_TEMPLATES
from .reasonableness.templates import TEMPLATES as REASONABLENESS_TEMPLATES
from .consistency.templates import TEMPLATES as CONSISTENCY_TEMPLATES
from .conformity.templates import TEMPLATES as CONFORMITY_TEMPLATES
from .uniqueness.templates import TEMPLATES as UNIQUENESS_TEMPLATES
from .integrity.templates import TEMPLATES as INTEGRITY_TEMPLATES

TEMPLATES: dict[str, dict[str, Any]] = {}
for group in (
    TIMELINESS_TEMPLATES,
    VALIDITY_TEMPLATES,
    COMPLETENESS_TEMPLATES,
    REASONABLENESS_TEMPLATES,
    CONSISTENCY_TEMPLATES,
    CONFORMITY_TEMPLATES,
    UNIQUENESS_TEMPLATES,
    INTEGRITY_TEMPLATES,
):
    duplicate_codes = set(TEMPLATES).intersection(group)
    if duplicate_codes:
        raise RuntimeError(f"Duplicate DQ check template codes: {sorted(duplicate_codes)}")
    TEMPLATES.update(group)
