def generate_title(text: str) -> str:
    # Simple title: first 5-7 words, capitalized
    words = text.strip().split()
    title = " ".join(words[:7])
    return title.capitalize()
