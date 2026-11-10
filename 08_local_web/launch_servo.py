from pathlib import Path
import runpy
import sys
app = Path(sys.argv[2])
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, str(app))
sys.argv = [str(app / 'server.py'), '--fake', '--host', '127.0.0.1', '--http-port', '8080']
runpy.run_path(str(app / 'server.py'), run_name='__main__')
