# Only for debugging
# You can log into an instance (SaladCloud or local) and check the changing files

import os

input_file  = os.path.join( os.path.dirname(__file__), 'data/input.txt'   ) # input
state_file  = os.path.join( os.path.dirname(__file__), 'data/state.txt'   ) # state
logs_file   = os.path.join( os.path.dirname(__file__), 'data/logs.txt'    ) # logs
output_file = os.path.join( os.path.dirname(__file__), 'data/output.txt' )  # output


try:
    with open( input_file ,'r' ) as f:
        print ( "-----> intput:" )
        # task = f.read().splitlines()
        task = f.read()
        print(task)

    with open( state_file,'r' ) as f:
        print ( "-----> state:" )
        # task = f.read().splitlines()
        task = f.read()
        print(task)

    with open( logs_file,'r' ) as f:
        print ( "-----> logs:" )
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