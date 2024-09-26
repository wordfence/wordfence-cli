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
            self.global_rules.append(rule)
        else:
            for table in rule.tables:
                if table not in self.table_rules:
                    self.table_rules[table] = []
                self.table_rules[table].append(rule)

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
            pre_validated: bool = False
        ) -> DatabaseRuleSet:
    if not pre_validated:
        JSON_VALIDATOR.validate(data)
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


def load_database_rules(path: bytes) -> DatabaseRuleSet:
    with open(path, 'rb') as file:
        data = json.load(file)
    return parse_database_rules(data)
