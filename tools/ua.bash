# bash completion for ubuntu-advantage-tools

_ua_complete()
{
    local cur_word prev_word
    cur_word="${COMP_WORDS[COMP_CWORD]}"
    prev_word="${COMP_WORDS[COMP_CWORD-1]}"

    subcmds="attach detach disable enable status version"
    base_params=""
    case ${COMP_CWORD} in
        1)
            COMPREPLY=($(compgen -W "$base_params $subcmds" -- $cur_word))
            ;;
        2)
            case ${prev_word} in
                disable)
                    COMPREPLY=($(compgen -W "cis-audit cc esm fips fips-updates livepatch" -- $cur_word))
                    ;;
                enable)
                    COMPREPLY=($(compgen -W "cis-audit cc esm fips fips-updates livepatch" -- $cur_word))
                    ;;
            esac
            ;;
        *)
            COMPREPLY=()
            ;;
    esac
}

complete -F _ua_complete ua

# vi: syntax=sh expandtab
