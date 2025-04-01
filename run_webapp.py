import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get port from environment or use default
port = int(os.getenv("WEBAPP_PORT", "8000"))

if __name__ == "__main__":
    # Run FastAPI app with uvicorn
    uvicorn.run(
        "app.webapp.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )