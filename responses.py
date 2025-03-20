from typing import List, Dict


def get_success_response(data: List, **kwargs) -> Dict:
    return {"status": "ok", "data": data, "error": None, **kwargs}


def get_error_response(error_code: int, message: str, **kwargs) -> Dict:
    return {"status": "error", "data": [], "error": {"code": error_code, "message": message}, **kwargs}
