#!/bin/bash
set -euo pipefail
docker exec poststeward-showcase-net test -f /tmp/network-ready
gh api --method POST repos/AyobamiH/poststeward-showcase/actions/runners/generate-jitconfig -f name="poststeward-showcase-web-$(date +%s)" -F runner_group_id=1 -f 'labels[]=poststeward-showcase' -f work_folder=_work --jq .encoded_jit_config |
docker run --rm -i --init --name poststeward-showcase-job --network container:poststeward-showcase-net --cap-drop ALL --security-opt no-new-privileges --pids-limit 400 --memory 2g --cpus 2 sha256:758e03ab2a553cf20f71c3495515d6966f125ca7bc1d94197597c4b25067e9f9 bash -ec 'IFS= read -r cfg; exec ./run.sh --jitconfig "$cfg"'
