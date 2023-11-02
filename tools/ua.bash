# bash completion for ubuntu-advantage-tools

. /etc/os-release  # For VERSION_ID

API_ENDPOINTS=$(/usr/bin/python3 -c 'from uaclient.api.api import VALID_ENDPOINTS; print(" ".join(VALID_ENDPOINTS))')
SERVICES="anbox-cloud cc-eal cis esm-apps esm-infra fips fips-updates landscape livepatch realtime-kernel ros ros-updates usg"

_ua_complete()
{
    local cur_word prev_word subcmds base_params
    cur_word="${COMP_WORDS[COMP_CWORD]}"
    prev_word="${COMP_WORDS[COMP_CWORD-1]}"

    subcmds="--debug --help --version api attach auto-attach collect-logs config detach disable enable fix help refresh security-status status system version"
    base_params=""

    case ${COMP_CWORD} in
        1)
            # shellcheck disable=SC2207
            COMPREPLY=($(compgen -W "$base_params $subcmds" -- $cur_word))
            ;;
        2)
            case ${prev_word} in
                disable)
                    # shellcheck disable=SC2207
                    COMPREPLY=($(compgen -W "$SERVICES" -- $cur_word))
                    ;;
                enable)
                    # shellcheck disable=SC2207
                    COMPREPLY=($(compgen -W "$SERVICES" -- $cur_word))
                    ;;
                api)
                    # shellcheck disable=SC2207
                    COMPREPLY=($(compgen -W "$API_ENDPOINTS" -- $cur_word))
                    ;;
            esac
            ;;
        *)
            COMPREPLY=()
            ;;
    esac
}

complete -F _ua_complete ua
complete -F _ua_complete pro

# vi: syntax=sh expandtab
