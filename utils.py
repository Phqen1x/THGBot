def split_message(message: str) -> list[str]:
    messages = []
    while len(message) > 2000:
        index = message[:2000].rfind("\n")
        if index == -1:
            index = 2000
        messages.append(message[:index])
        message = message[index:]
    messages.append(message)
    return messages
