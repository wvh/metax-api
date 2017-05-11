#!/bin/bash -xeu

# Run as the after_success step of a travis build.
echo $TRAVIS_BRANCH
if [[ "$TRAVIS_BRANCH" == "dev" ]]; then
    git clone https://github.com/CSCfi/metax-ops
    cd metax-ops/ansible/ && ansible-playbook -vv -i environments/development deploy.yml
elif [[ "$TRAVIS_BRANCH" == "staging" && "$TRAVIS_PULL_REQUEST" == "false" ]]; then
elif [[ "$TRAVIS_BRANCH" == "master" && "$TRAVIS_PULL_REQUEST" == "false" ]]; then
fi