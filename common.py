def is_number(n):
    try:
        int(n)
    except ValueError:
        return False
    return True