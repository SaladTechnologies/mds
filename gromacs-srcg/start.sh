#!/bin/bash

# Run the Jupyter Lab server
echo -e "\nRunning Jupyter Lab on port $JUPYTERLAB_PORT ..."
jupyter lab --no-browser --port=$JUPYTERLAB_PORT --ip=* --allow-root  --NotebookApp.token='' --NotebookApp.password='' &

# Run the main script and sleep to keep the container alive
echo -e "\nRunning main_salad.py ..."
python main_salad.py
