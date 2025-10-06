# Validate challenges
def validate_challenge_data(data, path):
    required_fields = ["uuid", "name", "description", "category", "value", "type", "state"]

    for field in required_fields:
        if field not in data:
            raise ValueError(f"{path}: Missing required field '{field}'")

    if not isinstance(data["uuid"], str):
        raise ValueError(f"{path}: 'uuid' must be a string")

    if not isinstance(data["name"], str) or len(data["name"]) > 80:
        raise ValueError(f"{path}: 'name' must be a string of up to 80 characters")

    if not isinstance(data["category"], str) or len(data["category"]) > 80:
        raise ValueError(f"{path}: 'category' must be a string of up to 80 characters")

    if not isinstance(data["description"], str):
        raise ValueError(f"{path}: 'description' must be a string")

    if not isinstance(data["value"], int) or data["value"] < 0:
        raise ValueError(f"{path}: 'value' must be a positive integer")

    if data["type"] not in ["standard"]:
        raise ValueError(f"{path}: 'type' is not valid")

    if data["state"] not in ["visible", "hidden"]:
        raise ValueError(f"{path}: 'state' is not valid")

    return data

def validate_flag_data(flag, path):
    required_fields = ["uuid", "type", "content"]

    for field in required_fields:
        if field not in flag:
            raise ValueError(f"{path}: Flag missing required field '{field}'")

    if not isinstance(flag["uuid"], str):
        raise ValueError(f"{path}: 'uuid' of flag must be a string")

    if flag["type"] not in ["static", "regex"]:
        raise ValueError(f"{path}: Flag type not supported")

    if not isinstance(flag["content"], str):
        raise ValueError(f"{path}: Flag content is not valid")

    if flag["data"] not in ["case_insensitive", ""]:
        raise ValueError(f"{path}: Flag data not supported")


def validate_tags_data(tags, path):
    if not isinstance(tags, list):
        raise ValueError(f"{path}: The 'tags' field must be a list.")
    for tag in tags:
        if not isinstance(tag, str):
            raise ValueError(f"{path}: Tags must be strings.")


def validate_hints_data(hints, path):
    if not isinstance(hints, list):
        raise ValueError(f"{path}: The 'hints' field must be a list.")

    for i, hint in enumerate(hints):
        if not isinstance(hint, dict):
            raise ValueError(f"{path}: Each hint must be a JSON object (index {i}).")

        required_fields = ["uuid", "title", "content", "type", "cost"]
        for field in required_fields:
            if field not in hint:
                raise ValueError(f"{path}: Missing required field '{field}' in hint (index {i}).")

        if not isinstance(hint["uuid"], str):
            raise ValueError(f"{path}: The 'uuid' field of the hint (index {i}) must be a string.")

        if not isinstance(hint["content"], str):
            raise ValueError(f"{path}: The 'content' field of the hint (index {i}) must be a string.")

        if not isinstance(hint["type"], str):
            raise ValueError(f"{path}: The 'type' field of the hint (index {i}) must be a string.")

        if not isinstance(hint["title"], str):
            raise ValueError(f"{path}: The 'title' field of the hint (index {i}) must be a string.")

        if not isinstance(hint["cost"], int):
            raise ValueError(f"{path}: The 'cost' field of the hint (index {i}) must be an integer.")


def validate_dynamic_data(dynamic, path):
    required_fields = ["initial", "minimum", "decay", "function"]

    for field in required_fields:
        if field not in dynamic:
            raise ValueError(f"{path}: Missing required field '{field}' for dynamic challenge")

    if not isinstance(dynamic["initial"], int) or dynamic["initial"] < 0:
        raise ValueError(f"{path}: 'initial' must be a non-negative integer for dynamic challenge")

    if not isinstance(dynamic["minimum"], int) or dynamic["minimum"] < 0:
        raise ValueError(f"{path}: 'minimum' must be a non-negative integer for dynamic challenge")

    if not isinstance(dynamic["decay"], int) or dynamic["decay"] < 0:
        raise ValueError(f"{path}: 'decay' must be a non-negative integer for dynamic challenge")

    if dynamic["function"] not in ["linear", "logarithmic"]:
        raise ValueError(f"{path}: 'function' must be either 'linear' or 'logarithmic' for dynamic challenge")

