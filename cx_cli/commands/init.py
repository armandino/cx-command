"""`cx init <shell>` — shell integration for pip-installed cx.

Prints shell code to stdout (plain text, no directives) so it can be eval'd:
    eval "$(cx init bash)"
"""

from __future__ import annotations

import sys

BASH_CODE = r'''# cx — directory navigation shell integration.

cx() {
    local output rc
    output="$(command cx "$@")"
    rc=$?

    if [ -z "$output" ]; then
        return "$rc"
    fi

    local last_line
    last_line="${output##*$'\n'}"

    if [[ "$last_line" == __CX__* ]]; then
        # Print everything except the directive line.
        local body="${output%$'\n'*}"
        if [ "$body" != "$output" ] && [ -n "$body" ]; then
            printf '%s\n' "$body"
        fi

        # Parse tab-delimited directive.
        local IFS=$'\t'
        local parts=($last_line)
        IFS=$' \t\n'
        local kind="${parts[1]}"

        case "$kind" in
            CD)
                builtin cd "${parts[2]}"
                return $?
                ;;
            OPEN)
                local -a cmd=("${parts[@]:2}")
                if [ "${#cmd[@]}" -eq 0 ]; then
                    printf 'cx: empty OPEN directive\n' >&2
                    return 1
                fi
                "${cmd[@]}" >/dev/null 2>&1 &
                disown 2>/dev/null || true
                return 0
                ;;
            EXEC)
                local cwd="${parts[2]}"
                local -a cmd=("${parts[@]:3}")
                ( builtin cd "$cwd" && "${cmd[@]}" )
                return $?
                ;;
            *)
                printf 'cx: unknown directive: %s\n' "$kind" >&2
                return 1
                ;;
        esac
    else
        printf '%s\n' "$output"
        return "$rc"
    fi
}

_cx_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    COMPREPLY=()

    # For `cx add <name> [-g <group>] <path>`, delegate to filesystem dir
    # completion when we're at the path position.
    if [ "$COMP_CWORD" -ge 3 ] && [ "${COMP_WORDS[1]}" = "add" ]; then
        local prev="${COMP_WORDS[COMP_CWORD-1]}"
        if [ "$prev" != "-g" ] && [ "$prev" != "--group" ]; then
            if [[ "$cur" != -* ]]; then
                if declare -F _filedir >/dev/null 2>&1; then
                    _filedir -d
                else
                    COMPREPLY=( $(compgen -d -- "$cur") )
                fi
                if [ "${#COMPREPLY[@]}" -gt 0 ]; then
                    return 0
                fi
            fi
        fi
    fi

    local candidates
    candidates="$(command cx __complete "$COMP_CWORD" "${COMP_WORDS[@]}" 2>/dev/null)"

    # Use newline as IFS so candidates with slashes stay intact.
    local IFS=$'\n'
    COMPREPLY=( $(compgen -W "$candidates" -- "$cur") )
}

complete -o nospace -F _cx_complete cx
'''


def run(shell: str) -> int:
    if shell == "bash":
        sys.stdout.write(BASH_CODE)
        return 0
    else:
        sys.stderr.write(f"cx: unsupported shell: {shell}\n")
        return 1
