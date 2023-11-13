from typing import Any

import jsons


def json_serialize(obj: Any) -> str:
    return jsons.dumps(obj, jdkwargs={"separators": (',', ':')})
