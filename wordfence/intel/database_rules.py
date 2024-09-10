from typing import Optional, Set


class DatabaseRule:

    def __init__(
                self,
                tables: Optional[Set[str]] = None,
                condition: Optional[str] = None
            ):
        self.tables = tables


class DatabaseRuleSet:
    pass
