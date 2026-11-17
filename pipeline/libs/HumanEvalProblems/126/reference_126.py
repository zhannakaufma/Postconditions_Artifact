def is_sorted_no_repeat(X):
    count_digit = dict([(i, 0) for i in X])
    for i in X:
        count_digit[i] += 1
    if any(count_digit[i] > 1 for i in X):
        return False
    if all(X[i-1] <= X[i] for i in range(1, len(X))):
        return True
    else:
        return False

