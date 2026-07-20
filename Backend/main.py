try:
    from flashrank import RerankRequest
except Exception:
    from Backend.vector_db import RerankRequest
try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except Exception:
    from Backend._compat_fastapi import FastAPI, CORSMiddleware

from Backend.routers import auth as auth_router
from Backend.routers import chat as chat_router
from Backend.routers import admin as admin_router


app = FastAPI()


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(admin_router.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


