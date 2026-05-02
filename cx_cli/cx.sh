# shellcheck shell=bash
# cx — directory navigation shell wrapper.
#
# Sourced from ~/.bashrc. Defines the cx() function and bash completion.
# The Python entry point (~/opt/user-settings/user-bin/cx) prints user output
# and — as its final stdout line — a tab-delimited directive:
#     __CX__<TAB>CD<TAB><path>
#     __CX__<TAB>OPEN<TAB><opener><TAB><path>
#     __CX__<TAB>EXEC<TAB><cwd><TAB><arg0><TAB><arg1>...
# We print everything except the directive line, then run it in the parent shell.

# Derive entry-point path from this script's location (robust if HOME changes).
# This file lives under cx_cli/, so cx is one level up.
_CX_PY="$(dirname "${BASH_SOURCE[0]}")/../cx"

cx() {
    # Capture stdout (preserve stderr live for errors). Trailing newlines are
    # stripped by $(), which is fine for line-oriented output.
    local output rc
    output="$("$_CX_PY" "$@")"
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
        # shellcheck disable=SC2206
        local parts=($last_line)
        IFS=$' \t\n'
        local kind="${parts[1]}"

        case "$kind" in
            CD)
                # shellcheck disable=SC2164
                builtin cd "${parts[2]}"
                return $?
                ;;
            OPEN)
                # parts[0]=__CX__, parts[1]=OPEN, parts[2..]=argv for opener
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

# -------- bash completion --------

_cx_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    COMPREPLY=()

    # For `cx add <name> [-g <group>] <path>`, delegate to filesystem dir
    # completion when we're at the path position (i.e. inside `cx add`, beyond
    # the alias name, and the previous word isn't a group flag).
    if [ "$COMP_CWORD" -ge 3 ] && [ "${COMP_WORDS[1]}" = "add" ]; then
        local prev="${COMP_WORDS[COMP_CWORD-1]}"
        if [ "$prev" != "-g" ] && [ "$prev" != "--group" ]; then
            # Skip dir completion when the *current* word looks like a flag —
            # let the python completer suggest -g/--group.
            if [[ "$cur" != -* ]]; then
                if declare -F _filedir >/dev/null 2>&1; then
                    _filedir -d
                else
                    COMPREPLY=( $(compgen -d -- "$cur") )
                fi
                # If python also has suggestions (e.g. group values), they
                # would have been emitted via __complete; but since add's
                # path slot is freeform, dir completion is the right answer.
                if [ "${#COMPREPLY[@]}" -gt 0 ]; then
                    return 0
                fi
            fi
        fi
    fi

    local candidates
    candidates="$("$_CX_PY" __complete "$COMP_CWORD" "${COMP_WORDS[@]}" 2>/dev/null)"

    # Use newline as IFS so candidates with slashes stay intact.
    local IFS=$'\n'
    # shellcheck disable=SC2207
    COMPREPLY=( $(compgen -W "$candidates" -- "$cur") )
}

complete -o nospace -F _cx_complete cx
