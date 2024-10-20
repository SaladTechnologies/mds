# Only for debugging
# You can log into an instance (SaladCloud or local) processing a job, and check the 3 folders

import os

input_file  = os.path.join( os.path.dirname(__file__), 'data/input/input.txt'   ) # input

state_file  = os.path.join( os.path.dirname(__file__), 'data/state/state.txt'   ) # state - running data
logs_file   = os.path.join( os.path.dirname(__file__), 'data/state/logs.txt'    ) # state - logs

output_file = os.path.join( os.path.dirname(__file__), 'data/output/output.txt' ) # output

try:
    with open( input_file ,'r' ) as f:
        print ( "-----> intput:" )
        # task = f.read().splitlines()
        task = f.read()
        print(task)

    with open( state_file,'r' ) as f:
        print ( "-----> state - running data:" )
        # task = f.read().splitlines()
        task = f.read()
        print(task)

    with open( logs_file,'r' ) as f:
        print ( "-----> state - logs:" )
        # task = f.read().splitlines()
        task = f.read()
        print(task)

    with open( output_file,'r' ) as f:
        print ( "-----> output:" )
        # task = f.read().splitlines()
        task = f.read()
        print(task)

except Exception as e:
    #print(str(e))
    pass