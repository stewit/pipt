def get_file_content(path):
    with open(path, "r", encoding="utf8") as f:
        content = f.read()

    return content
