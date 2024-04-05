from fastapi import Depends, FastAPI, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
from db.postgre import postgresql
import asyncio


load_dotenv()

@asynccontextmanager
async def init(app: FastAPI):
    print("connecting to databasese")
    await asyncio.gather(postgresql.connect())

    yield

    print("disconnecting from all databasese")
    await asyncio.gather(postgresql.disconnect())

def security_init(request: Request):
    setattr(request, "authorized", False)

app = FastAPI(
    title="satoshigpt",
    lifespan=init,
    docs_url=None,
    redoc_url=None,
    dependencies=[Depends(security_init)],
)
Instrumentator().instrument(app).expose(app)

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
) 

