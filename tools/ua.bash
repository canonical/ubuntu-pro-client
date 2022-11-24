# bash completion for ubuntu-advantage-tools

_ua_complete()
{
    local cur_word prev_word services subcmds base_params
    cur_word="${COMP_WORDS[COMP_CWORD]}"
    prev_word="${COMP_WORDS[COMP_CWORD-1]}"

    services=$(python3 -c "from uaclient.entitlements import valid_services; from uaclient.config import UAConfig; print(*valid_services(cfg=UAConfig()), sep=' ')
")
    subcmds=$(pro --help | awk '/^\s*$|^\s{5,}|Available|Use/ {next;} /Flags:/{check=1;next}/Use ubuntu-avantage/{check=0}check{ if ( $1 ~ /,/ ) { print $2} else print $1}')
    base_params=""
    case ${COMP_CWORD} in
        1)
            COMPREPLY=($(compgen -W "$base_params $subcmds" -- $cur_word))
            ;;
        2)
            case ${prev_word} in
                disable)
                    COMPREPLY=($(compgen -W "$services" -- $cur_word))
                    ;;
                enable)
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
