import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from core.apis.routers import call_router

load_dotenv()

app = FastAPI()


@app.on_event("startup")
async def startup_db_client():
    from core.db.database import connect_to_mongo

    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown_db_client():
    from core.db.database import close_mongo_connection

    await close_mongo_connection()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    return {"message": "Voice Bot Server is Running!"}


app.include_router(call_router.router)


if __name__ == "__main__":
    import asyncio
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    uvicorn.run(app, host="0.0.0.0", port=8000)
