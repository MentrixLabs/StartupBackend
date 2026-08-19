import uvicorn
from backend.main import app
import subprocess
import sys

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=80,
        reload=False
    )