# The 26 evaluated HumanEval functions
EVAL_ROWS = ["HumanEval/0", "HumanEval/37", "HumanEval/43", "HumanEval/47", "HumanEval/54", "HumanEval/57", "HumanEval/58", "HumanEval/82", "HumanEval/92", "HumanEval/93", "HumanEval/99", "HumanEval/100", "HumanEval/102", "HumanEval/104",
             "HumanEval/108", "HumanEval/112", "HumanEval/115", "HumanEval/119", "HumanEval/125", "HumanEval/128", "HumanEval/134",
             "HumanEval/141", "HumanEval/143", "HumanEval/148", "HumanEval/157", "HumanEval/161"]

# Qualtrics loop number of every function in survey_1_Raw.csv
QUALTRICS_LOOP = {"HumanEval/0": 1, "HumanEval/37": 2, "HumanEval/43": 3, "HumanEval/44": 4, "HumanEval/47": 5, "HumanEval/54": 6,
                  "HumanEval/57": 7, "HumanEval/58": 8, "HumanEval/80": 9, "HumanEval/82": 10, "HumanEval/92": 11, "HumanEval/93": 12,
                  "HumanEval/94": 13, "HumanEval/99": 14, "HumanEval/100": 15, "HumanEval/102": 16, "HumanEval/104": 17, "HumanEval/108": 18,
                  "HumanEval/111": 19, "HumanEval/112": 20, "HumanEval/115": 21, "HumanEval/119": 22, "HumanEval/125": 23, "HumanEval/128": 24,
                  "HumanEval/134": 25, "HumanEval/141": 26, "HumanEval/143": 27, "HumanEval/148": 28, "HumanEval/157": 29, "HumanEval/161": 30}

INPUTS_CAUGHT = [0.996703297, 0.828561886, 0.204476094, 0.685576666, 1, 0.505376344, 0.784618398, 0.728571429, 0.129858657,
                 0.979301448, 0.978373702, 0.95465587, 0.552309371, 0.778384076, 0.366684407, 0.630527513, 0.361065849,
                 0.954118297, 0.277132999, 0.30822301, 0.908163265, 0.986525505, 0.578312094, 0.431192661, 1, 0.89434018]

WRONG_POSTCONDITIONS = [
    "not return_value or any(abs(j-i) < threshold for i in numbers for j in numbers if i != j)",
    "all(return_value[i] <= return_value[i+2] for i in range(0, len(return_value), 2)) and all(l[i] == return_value[i] for i in range(0, len(l), 2))",
    "(return_value == True and any(-i in l for i in l)) or (return_value == False and not any(-i in l for i in l))",
    "(l.count(return_value) == 1 and len([i for i in l if i < return_value]) == len([i for i in l if i > return_value])) or (len([i for i in l if i <= return_value]) == len([i for i in l if i >= return_value]))",
    "return_value or all(char in s1 for char in s0)",
    "all((b - a > 0 for a, b in zip(l, l[1:])) if return_value else (b - a <= 0 for a, b in zip(l, l[1:])))",
    "return_value == sorted([value for value in l1 if value in l2 and return_value.count(value) == 1])",
    "(return_value and all(len(string) % i for i in range(2, int(len(string)**0.5) + 1)) and len(string) > 1) or (not return_value and not all(len(string) % i for i in range(2, int(len(string)**0.5) + 1)))",
    "(return_value == True) == ((x == y + z) or (y == x + z) or (z == x + y))",
    "all(m.lower() != r.lower() for m, r in zip(message, return_value))",
    "abs(float(value) - return_value) <= 0.5 and (return_value > 0 if float(value) > 0 else return_value <= 0)",
    "len(return_value) == n and return_value[0] == n and all(return_value[i] == return_value[i-1] + (2 if i%2 == n%2 else 1) for i in range(1, n))",
    "(return_value % 2 == 0 and x <= return_value <= y) or (x > y and return_value == -1)",
    "all(str(i) == ''.join(sorted(str(i))) and all(int(d) % 2 != 0 for d in str(i)) for i in return_value)",
    "return_value == len([num for num in arr if sum(int(digit) for digit in str(abs(num))) > 0])",
    "all(char not in return_value[0] for char in c) and return_value[0] == return_value[0][::-1] == return_value[1]",
    "isinstance(return_value, int) and return_value >= 0 and return_value <= sum(map(sum, grid)) / capacity",
    "(return_value in ['Yes', 'No']) and ((return_value == 'Yes' and all(lst[0].count(c) == lst[1].count(c) for c in ['(', ')'])) or (return_value == 'No' and not all(lst[0].count(c) == lst[1].count(c) for c in ['(', ')'])))",
    "all(isinstance(word, str) and ' ' not in word and ',' not in word for word in return_value) if isinstance(return_value, list) else 0 <= return_value <= 13",
    "(all(x >= 0 for x in arr) and return_value >= 0) or (any(x < 0 for x in arr) and return_value <= 0) or (len(arr) == 0 and return_value is None)",
    "return_value == (txt[-1].isalpha() and (len(txt) == 1 or txt[-2] == ' ')) if txt else False",
    "(return_value == 'Yes' and file_name.count('.') == 1) or (return_value == 'No' and file_name.count('.') != 1)",
    "all(len(word) in [2, 3, 5, 7] for word in return_value.split()) and all(word in sentence for word in return_value.split())",
    "all(planet in ['Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune'] for planet in return_value) and (planet1 in return_value or planet1 not in ['Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune']) and (planet2 in return_value or planet2 not in ['Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune']) and all(return_value[i] in ['Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune'][['Mercury', 'Venus','Earth', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune'].index(return_value[i-1])+1:] for i in range(1, len(return_value)))",
    "(return_value == True and c**2 == a**2 + b**2) or (return_value == False and c**2 != a**2 + b**2)",
    "all((c.isalpha() and c.swapcase() == r) or (not c.isalpha() and c == r) for c, r in zip(s, return_value))"
]

RIGHT_POSTCONDITIONS = [
    "(return_value == True) == any(abs(numbers[i] - numbers[j]) < threshold for i in range(len(numbers)) for j in range(i+1, len(numbers)))",
    "len(return_value) == len(l) and all(l[i] == return_value[i] for i in range(1, len(l), 2)) and all(return_value[i] <= return_value[i+2] for i in range(0, len(return_value)-2, 2))",
    "not return_value or any(x + y == 0 for i, x in enumerate(l) for j, y in enumerate(l) if i != j)",
    "sum(i <= return_value for i in l) >= len(l) // 2 and sum(i >= return_value for i in l) >= len(l) // 2",
    "(return_value == True and all(c in s1 for c in set(s0)) and all(c in s0 for c in set(s1))) or (return_value == False and not(all(c in s1 for c in set(s0)) and all(c in s0 for c in set(s1))))",
    "(all(l[i] <= l[i + 1] for i in range(len(l) - 1)) or all(l[i] >= l[i + 1] for i in range(len(l) - 1))) == return_value",
    "all(i in l1 and i in l2 for i in return_value) and return_value == sorted(set(return_value))",
    "(return_value and all(len(string) % i for i in range(2, int(len(string)**0.5) + 1)) and len(string) > 1) or not return_value",
    "((return_value == True) <= ((x == y+z or y == x+z or z == x+y) and all(isinstance(i, int) for i in [x, y, z])))",
    "all((c.lower() not in 'aeiou' and rv == c.swapcase()) or (c.lower() in 'aeiou' and rv == string.ascii_letters[string.ascii_letters.find(c.swapcase()) + 2]) for c, rv in zip(message, return_value))",
    "type(return_value) == int and abs(float(value) - return_value) <= 0.5 and (abs(float(value) - round(float(value))) != 0.5 or abs(return_value) >= abs(round(float(value))))",
    "all(return_value[i] == return_value[i-1] + 2 for i in range(1, n)) and len(return_value) == n",
    "(return_value == (max(i for i in range(x, y+1) if i%2 == 0) if x <= y and any(i%2 == 0 for i in range(x, y+1)) else -1))",
    "all(str(num)[i] in '13579' for num in return_value for i in range(len(str(num)))) and return_value == sorted(return_value)",
    "isinstance(return_value, int) and 0 <= return_value <= len(arr)",
    "all(ch not in return_value[0] for ch in c) and (return_value[0] == return_value[0][::-1]) == return_value[1]",
    "isinstance(return_value, int) and return_value >= sum(map(sum, grid)) // capacity",
    "(return_value == 'Yes' and lst[0].count('(') + lst[1].count('(') == lst[0].count(')') + lst[1].count(')')) or return_value == 'No'",
    "isinstance(return_value, list) if ' ' in txt or ',' in txt else isinstance(return_value, int)",
    "(isinstance(return_value, int) and len(arr) > 0) or (return_value is None and len(arr) == 0)",
    "not return_value or (txt[-1].isalpha() and (len(txt) == 1 or txt[-2] == ' '))",
    "(return_value == 'Yes' and (file_name[0].isalpha() and file_name.split('.')[1] in ['txt', 'exe', 'dll'])) or return_value == 'No'",
    "all(len(word) in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97] for word in return_value.split())",
    "all(planet in ['Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune'] for planet in return_value) and (planet1 != return_value[0] if return_value else True) and (planet2 != return_value[-1] if return_value else True)",
    "(return_value == True and (a**2 + b**2 == c**2 or a**2 + c**2 == b**2 or b**2 + c**2 == a**2)) or (return_value == False and not (a**2 + b**2 == c**2 or a**2 + c**2 == b**2 or b**2 + c**2 == a**2))",
    "all((ch.isalpha() and ch.swapcase() == s[i]) or (not ch.isalpha() and (ch == s[i] or ch == s[-(i+1)])) for i, ch in enumerate(return_value))"
]

WRONG_TYPE_CHECK = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0]
WRONG_FORMAT_CHECK = [0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1]
WRONG_ARITHMETIC_BOUNDS = [1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0]
WRONG_ARITHMETIC_EQUALITY = [0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1]
WRONG_CONTAINER_PROPERTY = [0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0]
WRONG_ELEMENT_PROPERTY = [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
WRONG_FORALL_ELEMENT_PROPERTY = [1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1] 
WRONG_IMPLICATION = [1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1,]
WRONG_NULL_CHECK = [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]

RIGHT_TYPE_CHECK = [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0]
RIGHT_FORMAT_CHECK = [0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1]
RIGHT_ARITHMETIC_BOUNDS = [1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
RIGHT_ARITHMETIC_EQUALITY = [0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0]
RIGHT_CONTAINER_PROPERTY = [0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0]
RIGHT_ELEMENT_PROPERTY = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0]
RIGHT_FORALL_ELEMENT_PROPERTY = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1]
RIGHT_IMPLICATION = [1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1]
RIGHT_NULL_CHECK = [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0]
