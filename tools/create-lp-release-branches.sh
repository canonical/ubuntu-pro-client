#!/usr/bin/bash

DRY_RUN_USAGE="usage: env DEVEL_RELEASE=impish UA_VERSION=27.3 SRU_BUG=1942929 LP_USER=username bash tools/create-lp-release-branches.sh"
DO_IT_USAGE="usage: env DO_IT=1 DEVEL_RELEASE=impish UA_VERSION=27.3 SRU_BUG=1942929 LP_USER=username bash tools/create-lp-release-branches.sh"

if [ -z "$DEVEL_RELEASE" ]; then
  echo "please set DEVEL_RELEASE"
  echo "$DRY_RUN_USAGE"
  exit 1
fi
if [ -z "$UA_VERSION" ]; then
  echo "please set UA_VERSION"
  echo "$DRY_RUN_USAGE"
  exit 1
fi
if [ -z "$SRU_BUG" ]; then
  echo "please set SRU_BUG"
  echo "$DRY_RUN_USAGE"
  exit 1
fi
if [ -z "$LP_USER" ]; then
  echo "please set LP_USER"
  echo "$DRY_RUN_USAGE"
  exit 1
fi

if [ -z "$DO_IT"  ]; then
  echo "This is a dry run. To actually run set DO_IT=1"
  echo "$DO_IT_USAGE"
else
  set -x
  set -e
fi

for release in xenial bionic focal hirsute
do
  echo
  echo $release

  checkout_cmd="git checkout upload-${UA_VERSION}-${DEVEL_RELEASE} -B upload-${UA_VERSION}-$release"
  if [ -z "$DO_IT" ]; then
    echo "$checkout_cmd"
  else
    $checkout_cmd
  fi

  case "${release}" in
      xenial) version=${UA_VERSION}~16.04.1;;
      bionic) version=${UA_VERSION}~18.04.1;;
      focal) version=${UA_VERSION}~20.04.1;;
      hirsute) version=${UA_VERSION}~21.04.1;;
  esac
  dch_cmd=(dch -v ${version} -D ${release} -b  "Backport new upstream release: (LP: #${SRU_BUG}) to $release")
  if [ -z "$DO_IT" ]; then
    echo "${dch_cmd[@]}"
  else
    "${dch_cmd[@]}"
  fi

  commit_cmd=(git commit -m "changelog backport to ${release}" debian/changelog)
  if [ -z "$DO_IT" ]; then
    echo "${commit_cmd[@]}"
  else
    "${commit_cmd[@]}"
  fi

  push_cmd="git push $LP_USER upload-${UA_VERSION}-$release"
  if [ -z "$DO_IT" ]; then
    echo "$push_cmd"
  else
    $push_cmd
  fi
done

if [ -z "$DO_IT"  ]; then
  echo
  echo "This was a dry run. To actually run set DO_IT=1"
  echo "$DO_IT_USAGE"
fi
