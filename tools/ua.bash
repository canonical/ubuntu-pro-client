# bash completion for ubuntu-advantage-tools

. /etc/os-release  # For VERSION_ID

_ua_complete()
{
    local cur_word prev_word services subcmds base_params
    cur_word="${COMP_WORDS[COMP_CWORD]}"
    prev_word="${COMP_WORDS[COMP_CWORD-1]}"

    if [ "$VERSION_ID" = "16.04" ] || [ "$VERSION_ID" == "18.04" ]; then
        services="anbox-cloud cc-eal cis esm-apps esm-infra fips fips-updates landscape livepatch realtime-kernel ros ros-updates"
    else
        services="anbox-cloud cc-eal esm-apps esm-infra fips fips-updates landscape livepatch realtime-kernel ros ros-updates usg"
    fi

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
                    COMPREPLY=($(compgen -W "$services" -- $cur_word))
                    ;;
                enable)
                    # shellcheck disable=SC2207
                    COMPREPLY=($(compgen -W "$services" -- $cur_word))
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
