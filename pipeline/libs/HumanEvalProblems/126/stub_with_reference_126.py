def is_sorted_no_repeat(X):
    '''
    Given a list of numbers, return whether or not they are sorted
    in ascending order. If list has more than 1 of any number,
    return False. Assume no negative numbers and only integers.

    Examples
    is_sorted([5]) ➞ True
    is_sorted([1, 3, 4, 5]) ➞ True
    is_sorted([1, 4, 3, 5]) ➞ False
    is_sorted([1, 2, 2, 3, 4]) ➞ False
    '''

    count_digit = dict([(i, 0) for i in X])
    for i in X:
        count_digit[i] += 1
    if any(count_digit[i] > 1 for i in X):
        return False
    if all(X[i-1] <= X[i] for i in range(1, len(X))):
        return True
    else:
        return False

