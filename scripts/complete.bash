#!/usr/bin/env bash

function _wordfence_complete() {
	result_string=$(python3 -m wordfence.cli.auto_complete ${COMP_WORDS[*]} ${COMP_CWORD})
	result=()
	while IFS= read -r line
	do
		result+=("$line")
	done <<< "$result_string"
	words="${result[0]}"
	flags=""
	if [ "${result[1]}" ]
	then
		flags="${flags}-f "
	fi
	if [ "${result[2]}" ]
	then
		flags="${flags}-d "
	fi
	latest="${COMP_WORDS[$COMP_CWORD]}"
	COMPREPLY=($(compgen ${flags}-W "$words" -- "$latest"))
	return 0
}

complete -F _wordfence_complete wordfence
