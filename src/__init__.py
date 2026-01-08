from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from src.db.main import init_db
from src.db.redis import redis_client, check_redis_connection
from src.auth.routes import authRouter
from src.elections.routes import electionRouter
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.db.main import DbCleanup


scheduler = AsyncIOScheduler()
db_cleanup = DbCleanup()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n---Server Started---\n")
    
    # 1. Initialize Postgres
    await init_db()
    
    # 2. Check Redis Connection
    await check_redis_connection()
    scheduler.add_job(db_cleanup.users_cleanup, 'interval', days=1)
    scheduler.add_job(db_cleanup.universal_otp_cleanup, 'interval', minutes=30)
    
    scheduler.start()
    yield
    
    # 3. Clean up Redis connections on shutdown
    print("---Closing Redis Connection---")
    await redis_client.close()
    print("---Server Closed---")

app = FastAPI(
    title="Dvota API",
    description="Endpoints for Dvota",
    lifespan = lifespan
)

from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:3000",
    "http://localhost:5173",  
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://dvota.netlify.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Server Health"])
def health_check():
    return{
        "status": "Success",
        "message": "Server Working"
    }




@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None
        }
    )


def format_validation_errors(errors):
    formatted = []
    for err in errors:
        field = ".".join(str(loc) for loc in err["loc"][1:])
        formatted.append({
            "field": field,
            "message": err["msg"]
        })
    return formatted


@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request:Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "success": False,
            "message": "Validation error",
            "errors": format_validation_errors(exc.errors()),
            "data": None
        }
    )
app.include_router(authRouter, prefix="/api/auth", tags=["Auth"])
app.include_router(electionRouter, prefix="/api/elections", tags=["Election"])