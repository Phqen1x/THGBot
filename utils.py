def split_message(message: str) -> list[str]:
    messages = []

    while len(message) > 2000:
        index = message[:2000].rfind("\n")

        if index == -1:
            index = 2000

        # Check if "EQUIPPED" appears in what we're about to split
        if "EQUIPPED" in message[:index]:
            # Find the position of "EQUIPPED" (case-sensitive)
            equipped_pos = message[:index].rfind("EQUIPPED")

            # Find the newline before the marker
            safe_split = message[:equipped_pos].rfind("\n")

            if safe_split > 0:
                # Split before the "EQUIPPED" line
                index = safe_split
            # else: keep original index if "EQUIPPED" is at the very start

        messages.append(message[:index])
        message = message[index:]

    messages.append(message)
    return messages
