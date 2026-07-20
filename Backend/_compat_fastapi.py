from typing import Any, Callable

class FastAPI:
    def __init__(self, *args, **kwargs):
        pass
    def add_middleware(self, *args, **kwargs):
        pass
    def include_router(self, router: Any):
        pass

class CORSMiddleware:
    def __init__(self, *args, **kwargs):
        pass

class APIRouter:
    def __init__(self, *args, **kwargs):
        pass
    def _make_decorator(self):
        def dec(func: Callable):
            return func
        return lambda *a, **k: self._make_decorator()
    def get(self, *args, **kwargs):
        return self._make_decorator()
    def post(self, *args, **kwargs):
        return self._make_decorator()
    def delete(self, *args, **kwargs):
        return self._make_decorator()

def Depends(x=None):
    return x

class Header:
    def __init__(self, default=None):
        self.default = default

class HTTPException(Exception):
    def __init__(self, status_code=500, detail=""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")

class status:
    HTTP_401_UNAUTHORIZED = 401
    HTTP_423_LOCKED = 423
    HTTP_429_TOO_MANY_REQUESTS = 429

class StreamingResponse:
    def __init__(self, gen, media_type=None):
        self.gen = gen
        self.media_type = media_type
