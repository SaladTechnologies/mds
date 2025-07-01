#!/bin/bash

# Run the Jupyter Lab server
echo -e "\nRunning Jupyter Lab on port $JUPYTERLAB_PORT ..."
jupyter lab --no-browser --port=$JUPYTERLAB_PORT --ip=* --allow-root  --NotebookApp.token='' --NotebookApp.password='' &

# Keep the container alive
sleep infinity