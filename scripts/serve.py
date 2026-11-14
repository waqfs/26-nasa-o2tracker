"""Production entry point for a user-authorized hosting environment."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import uvicorn

if __name__=='__main__':
    uvicorn.run('backend.app:app',host='0.0.0.0',port=int(os.environ.get('PORT','8010')))
