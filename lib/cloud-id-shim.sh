#!/bin/sh

RUN_CLOUD_INIT=/run/cloud-init
if [ ! -d "$RUN_CLOUD_INIT" ]; then
  exit 0
fi

CLOUD_ID_LINK_PATH=$RUN_CLOUD_INIT/cloud-id
if [ -L "$CLOUD_ID_LINK_PATH" ]; then
  exit 0
fi

CLOUD_ID=$(cloud-id 2>/dev/null) || CLOUD_ID=""
if [ -z "$CLOUD_ID" ]; then
  exit 0
fi

CLOUD_ID_FILE_PATH=$RUN_CLOUD_INIT/cloud-id-$CLOUD_ID

echo "$CLOUD_ID" > "$CLOUD_ID_FILE_PATH"
ln -s "$CLOUD_ID_FILE_PATH" "$CLOUD_ID_LINK_PATH"
echo "Created symlink $CLOUD_ID_LINK_PATH -> $CLOUD_ID_FILE_PATH." >&2

exit 0
