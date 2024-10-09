#!/usr/bin/bash

DRY_RUN_USAGE="usage: env RELEASES=\"xenial bionic focal jammy\" PRO_VERSION=27.3 SRU_BUG=1942929 bash tools/create-gh-release-branches.sh"

if [ -z "$RELEASES" ]; then
  echo "please set RELEASES"
  echo "$DRY_RUN_USAGE"
  exit 1
fi
if [ -z "$PRO_VERSION" ]; then
  echo "please set PRO_VERSION"
  echo "$DRY_RUN_USAGE"
  exit 1
fi
if [ -z "$SRU_BUG" ]; then
  echo "please set SRU_BUG"
  echo "$DRY_RUN_USAGE"
  exit 1
fi

if [ -z "$DO_IT"  ]; then
  echo "This is a dry run. To actually run set DO_IT=1"
else
  set -x
  set -e
fi

for release in $RELEASES
do
  echo
  echo $release

  checkout_cmd="git checkout main -B release-${PRO_VERSION}-$release"
  if [ -z "$DO_IT" ]; then
    echo "$checkout_cmd"
  else
    $checkout_cmd
  fi

  case "${release}" in
      xenial) version=${PRO_VERSION}~16.04;;
      bionic) version=${PRO_VERSION}~18.04;;
      focal) version=${PRO_VERSION}~20.04;;
      jammy) version=${PRO_VERSION}~22.04;;
      noble) version=${PRO_VERSION}~24.04;;
  esac
  dch_cmd=(dch -m -v "${version}" -D "${release}" -b  "Backport $PRO_VERSION to $release (LP: #${SRU_BUG})")
  if [ -z "$DO_IT" ]; then
    echo "${dch_cmd[@]}"
  else
    "${dch_cmd[@]}"
  fi

  commit_cmd=(git commit -m "backport ${PRO_VERSION} to ${release}" debian/changelog)
  if [ -z "$DO_IT" ]; then
    echo "${commit_cmd[@]}"
  else
    "${commit_cmd[@]}"
  fi

  push_cmd="git push origin release-${PRO_VERSION}-$release"
  if [ -z "$DO_IT" ]; then
    echo "$push_cmd"
  else
    $push_cmd
  fi
done

if [ -z "$DO_IT"  ]; then
  echo
  echo "This was a dry run. To actually run set DO_IT=1"
  echo "env DO_IT=1 RELEASES=\"${RELEASES}\" PRO_VERSION=${PRO_VERSION} SRU_BUG=${SRU_BUG} bash tools/create-gh-release-branches.sh"
fi
