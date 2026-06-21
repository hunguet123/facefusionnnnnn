from argparse import ArgumentParser, _ArgumentGroup, _SubParsersAction
from typing import List, Optional, Tuple


def find_argument_group(program : ArgumentParser, group_name : str) -> Optional[_ArgumentGroup]:
	for group in program._action_groups:
		if group.title == group_name:
			return group
	return None


def validate_args(program : ArgumentParser) -> bool:
	if validate_actions(program):
		for action in program._actions:
			if isinstance(action, _SubParsersAction):
				for _, sub_program in action._name_parser_map.items():
					if not validate_args(sub_program):
						return False
		return True
	return False


def collect_invalid_actions(program : ArgumentParser) -> List[Tuple[str, object, List[object]]]:
	invalid_actions : List[Tuple[str, object, List[object]]] = []

	for action in program._actions:
		if action.default and action.choices:
			choices = list(action.choices)

			if isinstance(action.default, list):
				invalid_values = [ default for default in action.default if default not in action.choices ]

				if invalid_values:
					invalid_actions.append((action.dest, action.default, choices))
			elif action.default not in action.choices:
				invalid_actions.append((action.dest, action.default, choices))

		if isinstance(action, _SubParsersAction):
			for _, sub_program in action._name_parser_map.items():
				invalid_actions.extend(collect_invalid_actions(sub_program))

	return invalid_actions


def validate_actions(program : ArgumentParser) -> bool:
	return not collect_invalid_actions(program)
