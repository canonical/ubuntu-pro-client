#!/bin/bash

set -e

sudo apt-get update
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev \
libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev xz-utils \
tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev clang

curl http://pyenv.run | bash

export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# gcc will segfault while compiling some python versions
export CC=clang

pyenv install 3.10.4
pyenv install 3.8.10
pyenv install 3.6.9
# Xenial has 3.5.2, which requires old libssl and is not worth it for the tests
pyenv install 3.5.3

pyenv local 3.10.4 3.8.10 3.6.9 3.5.3

python -m pip install tox
python -m pip install tox-setuptools-version
python -m pip install tox-pyenv
