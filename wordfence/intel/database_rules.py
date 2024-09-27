from wordfence.util.validation import ListValidator, DictionaryValidator, \
    OptionalValueValidator
from typing import Optional, Set, List
import json


class DatabaseRule:

    def __init__(
                self,
                identifier: int,
                tables: Optional[Set[str]] = None,
                condition: Optional[str] = None,
                description: Optional[str] = None
            ):
        self.identifier = identifier
        self.tables = tables
        self.condition = condition
        self.description = description

    def __hash__(self):
        return hash(self.identifier)

    def __eq__(self, other) -> bool:
        return (
                type(other) is type(self)
                and other.identifier == self.identifier
            )


class DatabaseRuleSet:

    def __init__(self):
        self.rules = {}
        self.table_rules = {}
        self.global_rules = set()

    def add_rule(self, rule: DatabaseRule) -> None:
        if rule.identifier in self.rules:
            raise Exception('Duplicate rule ID: {rule.identifier}')
        self.rules[rule.identifier] = rule
        if rule.tables is None:
            self.global_rules.add(rule)
        else:
            for table in rule.tables:
                if table not in self.table_rules:
                    self.table_rules[table] = set()
                self.table_rules[table].add(rule)

    def remove_rule(self, rule_id: int) -> None:
        try:
            rule = self.rules.pop(rule_id)
            if rule.tables is None:
                self.global_rules.discard(rule)
            else:
                for table in rule.tables:
                    if table in list(self.table_rules.keys()):
                        table_rules = self.table_rules[table]
                        table_rules.discard(rule)
                        if len(table_rules) == 0:
                            del self.table_rules[table]
        except KeyError:
            pass  # Rule doesn't exist, no need to remove

    def get_rules(self, table: str) -> List[DatabaseRule]:
        rules = []
        try:
            rules.extend(self.table_rules[table])
        except KeyError:
            pass  # There are no table rules
        rules.extend(self.global_rules)
        return rules

    def get_targeted_tables(self) -> List[str]:
        return self.table_rules.keys()

    def get_rule(self, identifier: int) -> DatabaseRule:
        return self.rules[identifier]

    def filter_rules(
                self,
                included: Optional[Set[int]] = None,
                excluded: Optional[Set[int]] = None
            ):
        if included is not None:
            for rule_id in list(self.rules.keys()):
                if rule_id not in included:
                    self.remove_rule(rule_id)
        if excluded is not None:
            for rule_id in excluded:
                self.remove_rule(rule_id)


JSON_VALIDATOR = ListValidator(
        DictionaryValidator({
                'id': int,
                'tables': ListValidator(str),
                'condition': str,
                'description': OptionalValueValidator(str)
            }, optional_keys={'description'})
    )


def parse_database_rules(
            data,
            pre_validated: bool = False,
            rule_set: Optional[DatabaseRuleSet] = None
        ) -> DatabaseRuleSet:
    if not pre_validated:
        JSON_VALIDATOR.validate(data)
    if rule_set is None:
        rule_set = DatabaseRuleSet()
    for rule_data in data:
        rule = DatabaseRule(
                identifier=rule_data['id'],
                tables=rule_data['tables'],
                condition=rule_data['condition'],
                description=rule_data['description']
            )
        rule_set.add_rule(rule)
    return rule_set


def load_database_rules(
            path: bytes,
            rule_set: Optional[DatabaseRuleSet] = None
        ) -> DatabaseRuleSet:
    with open(path, 'rb') as file:
        data = json.load(file)
    return parse_database_rules(data, rule_set=rule_set)
