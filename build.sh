#!/bin/bash

set -e

export AWS_DEFAULT_REGION=eu-west-1

image_tag=$(basename $PWD)

docker image build -qt $image_tag . >/dev/null &
build_pid=$!

echo -n Building docker image.. >&2
while kill -0 $build_pid 2>/dev/null; do
    echo -n . >&2
    sleep 1
done
wait $build_pid

echo done. >&2

echo built $image_tag
