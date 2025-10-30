from vira.app import App
from vira.api_router import ApiRouter
from vira.background_tasks import get_background_tasks, create_task
from vira.http_responses import OK_JSONResponse
from vira.request_data import RequestData
from vira.types import Methods

router1 = ApiRouter()

async def home_bg_task(_) -> None:
    print("home bg task triggered")

@router1.get("/home")
async def home():
    bg_task = get_background_tasks()
    await bg_task.add_tasks([create_task(home_bg_task)])
    print("home triggered")

    return OK_JSONResponse()

@router1.get("/")
async def root():
    print("root triggered")
    return OK_JSONResponse()

router2 = ApiRouter()
@router2.get("/about")
async def about():
    print("about triggered")
    # server should return 500 error because we are returning none as response


def qs_extractor(qs: dict) -> dict:
    return qs

def body_extractor(body: bytes) -> int:
    return 1

@router2.multi_methods(
    "/about/careers",
    [Methods.GET, Methods.POST],
    qs_extractor,
    body_extractor
)
async def about(request_data: RequestData[dict, int]):
    print("about careers triggered")
    qs = await request_data.get_query_string_params()
    body_stream = bytearray(*[ch async for ch in request_data.get_stream_body_bytes()])
    print(body_stream)
    body_custom = await request_data.get_body()
    print(body_custom)
    body_json = await request_data.get_json_body()
    print(body_json)

    return OK_JSONResponse()


app = App()
app.include_routes([router1, router2])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)