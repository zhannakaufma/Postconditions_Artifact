import pandas as pd
from libs.demographics_maps import DEVELOPER_MAP, YEARS_PROGRAMMING_MAP, LLM_USE_MAP, KNOW_PYTHON_MAP, ASSERTION_EXPERIENCE_MAP, AI_USE_MAP, WRITE_PYTHON_MAP
import numpy as np
import json
import Levenshtein
import importlib.util
import inspect
import string
import random
import pprint
from libs.postconditions_info import (EVAL_ROWS, QUALTRICS_LOOP, INPUTS_CAUGHT, WRONG_POSTCONDITIONS, RIGHT_POSTCONDITIONS,
                                      WRONG_TYPE_CHECK, WRONG_FORMAT_CHECK, WRONG_ARITHMETIC_BOUNDS,
                                      WRONG_ARITHMETIC_EQUALITY, WRONG_CONTAINER_PROPERTY, WRONG_ELEMENT_PROPERTY,
                                      WRONG_FORALL_ELEMENT_PROPERTY, WRONG_IMPLICATION,
                                      WRONG_NULL_CHECK, RIGHT_TYPE_CHECK, RIGHT_FORMAT_CHECK, RIGHT_ARITHMETIC_BOUNDS,
                                      RIGHT_ARITHMETIC_EQUALITY, RIGHT_CONTAINER_PROPERTY,
                                      RIGHT_ELEMENT_PROPERTY, RIGHT_FORALL_ELEMENT_PROPERTY, RIGHT_IMPLICATION, RIGHT_NULL_CHECK)
from libs.complexity_metrics import classic_metrics, function_metrics
from libs.shevrin_maoz_metrics import sm_table, PROPERTIES

CAPTURE_MAP = {
    "none": 0,
    "some": 1,
    "about half": 2,
    "most": 3,
    "all": 4
}

total_tests_per_function = []
total_tests_failed_per_function_right_postcon = []
total_tests_failed_per_function_wrong_postcon = []
total_syntax_error_per_function_wrong_postcon = []
total_value_error_per_function_wrong_postcon = []
total_type_error_per_function_wrong_postcon = []
total_index_error_per_function_wrong_postcon = []
total_assertion_error_per_function_wrong_postcon = []
for functionloc, wrongpostconsnip, rightpostconsnip in zip(EVAL_ROWS, WRONG_POSTCONDITIONS, RIGHT_POSTCONDITIONS):
    wrongpostcon = "assert " + wrongpostconsnip
    rightpostcon = "assert " + rightpostconsnip
    if functionloc == "HumanEval/94":
        wrongpostcon = "assert isinstance(return_value, int) and return_value >= 0 and return_value <= max(sum(map(int, str(abs(num)))) for num in lst)"
    if functionloc == "HumanEval/37":
        wrongpostcon = "assert all(return_value[i] <= return_value[i+2] for i in range(0, len(return_value)-2, 2)) and all(l[i] == return_value[i] for i in range(0, len(l), 2))"

    with open("./libs/HumanEvalPlus.jsonl", "r") as f: 
        for jline in f.readlines():
            loadedline = json.loads(jline)
            if loadedline["task_id"] == functionloc:
                full_input = loadedline["base_input"] + loadedline["plus_input"]
                functionpath = "libs/HumanEvalProblems/" + functionloc.split("/")[1] + "/stub_with_reference_" + functionloc.split("/")[1] + ".py"

                # Load the module from the file path
                spec = importlib.util.spec_from_file_location("module_name", functionpath)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Now access the function (you need to know the function name)
                # For HumanEval, the function name is in task["entry_point"]
                canonical_func = getattr(module, loadedline["entry_point"])
                sig = inspect.signature(canonical_func)

                # Get parameter names as a list
                param_names = list(sig.parameters.keys())
                total_tests = 0
                tests_failed_right_postcon = 0
                tests_failed_wrong_postcon = 0
                syntax_error_wrong_postcon = 0
                value_error_wrong_postcon = 0
                type_error_wrong_postcon = 0
                assertion_error_wrong_postcon = 0
                index_error_wrong_postcon = 0
                for input_args in full_input:
                    total_tests += 1
                    # Create a namespace with the input variables
                    namespace = {name: value for name, value in zip(param_names, input_args)}

                    # Add the return value
                    namespace['return_value'] = canonical_func(*input_args)
                    if "string" not in param_names:
                        namespace['string'] = string  
                    try:
                        exec(rightpostcon, namespace)  # Will raise AssertionError if it fails
                    except AssertionError:
                        tests_failed_right_postcon += 1
                    except ValueError:
                        tests_failed_right_postcon += 1
                    try:
                        exec(wrongpostcon, namespace)  # Will raise AssertionError if it fails
                    except AssertionError:
                        assertion_error_wrong_postcon += 1
                        tests_failed_wrong_postcon += 1
                    except (TypeError):
                        type_error_wrong_postcon += 1
                        tests_failed_wrong_postcon += 1
                    except (SyntaxError):
                        syntax_error_wrong_postcon += 1
                        tests_failed_wrong_postcon += 1
                    except (IndexError):
                        index_error_wrong_postcon += 1
                        tests_failed_wrong_postcon += 1
                    except (ValueError):
                        value_error_wrong_postcon += 1
                        tests_failed_wrong_postcon += 1
                        
                total_tests_per_function.append(total_tests)
                total_tests_failed_per_function_right_postcon.append(tests_failed_right_postcon)
                total_tests_failed_per_function_wrong_postcon.append(tests_failed_wrong_postcon)
                total_syntax_error_per_function_wrong_postcon.append(syntax_error_wrong_postcon)
                total_value_error_per_function_wrong_postcon.append(value_error_wrong_postcon)
                total_type_error_per_function_wrong_postcon.append(type_error_wrong_postcon)
                total_assertion_error_per_function_wrong_postcon.append(assertion_error_wrong_postcon)
                total_index_error_per_function_wrong_postcon.append(index_error_wrong_postcon)
                if assertion_error_wrong_postcon == 0:
                    print("no assertion errors")
                    print(functionloc)

percentage_tests_failed_per_wrong_postcon = []

for total, failed in zip(total_tests_per_function, total_tests_failed_per_function_wrong_postcon):
    percentage_tests_failed_per_wrong_postcon.append(failed/total)

percentage_tests_failed_per_right_postcon = []

for total, failed in zip(total_tests_per_function, total_tests_failed_per_function_right_postcon):
    percentage_tests_failed_per_right_postcon.append(failed/total)

WRONG_SM = sm_table(WRONG_POSTCONDITIONS)
RIGHT_SM = sm_table(RIGHT_POSTCONDITIONS)
for problem, wrong, right, wrong_formula, right_formula in zip(EVAL_ROWS, WRONG_POSTCONDITIONS, RIGHT_POSTCONDITIONS, WRONG_SM.SM_Formula, RIGHT_SM.SM_Formula):
    print(f"{problem} incorrect: {wrong}\n    => {wrong_formula}\n{problem} correct:   {right}\n    => {right_formula}")

# Function-level metrics (complexity, size, docstring length and worked examples) of
# each HumanEval function, from its stub_with_reference file.
FUNCTION_METRICS = {problem: function_metrics(open(f"libs/HumanEvalProblems/{problem.split('/')[1]}/stub_with_reference_{problem.split('/')[1]}.py").read())
                    for problem in EVAL_ROWS}

class Result:
    # Fields that stay constant when result is exploded into multiple rows.

    def __init__(self, series, pid) -> None:
        row_template = {}

        row_template["Pid"] = pid

        row_template["Age"] = series["Q1"]

        row_template["Is_Developer"] = DEVELOPER_MAP[series["Q474"]]

        row_template["Programming_Seniority"] = YEARS_PROGRAMMING_MAP[series["Q525"]]

        row_template["LLM_Use"] = LLM_USE_MAP[series["Q507"]]

        row_template["Python_Knowledge"] = KNOW_PYTHON_MAP[series["Q510"]]

        row_template["Python_Use"] = WRITE_PYTHON_MAP[series["Q508"]]

        row_template["Assertion_Experience"] = ASSERTION_EXPERIENCE_MAP[series["Q505"]]

        row_template["AI_Use"] = AI_USE_MAP[series["Q506"]]

        self.row_template = row_template
        self.series = series
        self.timing = []
    
    def long_table_rows(self):
        attn_checks_passed = 0
        for loopnum in [4, 7, 11]:
            Function_Seen = self.series["seen" + str(loopnum)]

            if Function_Seen == "0":
                attn_checks_passed = -100
                break

            elif Function_Seen == "":
                attn_checks_passed = -100
                break

            loopseen = QUALTRICS_LOOP[Function_Seen]   # Qualtrics numbered the loops by the original 30-function design

            this_check_passed = True
            if self.series[str(loopseen) + "_Pass"] != "attention check":
                this_check_passed = False

            if self.series[str(loopseen) + "_Capture"] != "attention check":
                this_check_passed = False

            if this_check_passed:
                attn_checks_passed += 1

        for loopnum in [1, 2, 3, 5, 6, 8, 9, 10, 12, 13]:
            Function_Seen = self.series["seen" + str(loopnum)]

            if Function_Seen == "0":
                attn_checks_passed = -100
                break

            elif Function_Seen == "":
                attn_checks_passed = -100
                break

            loopseen = QUALTRICS_LOOP[Function_Seen]   # Qualtrics numbered the loops by the original 30-function design

            this_check_passed = True
            if "attention check" in self.series[str(loopseen) + "_Pass"]:
                this_check_passed = False

            if "attention check" in self.series[str(loopseen) + "_Capture"]:
                this_check_passed = False

            if not this_check_passed:
                attn_checks_passed -= 1
        if (attn_checks_passed < 3):
            return

        for loopnum in [1, 2, 3, 5, 6, 8, 9, 10, 12, 13]:
            new_row = {}
            new_row.update(self.row_template)

            Function_Seen = self.series["seen" + str(loopnum)]
            if Function_Seen not in EVAL_ROWS:   # shown (and used as an attention check) but not analysed
                continue

            actual_capture = INPUTS_CAUGHT[EVAL_ROWS.index(Function_Seen)]

            loopseen = QUALTRICS_LOOP[Function_Seen]   # Qualtrics numbered the loops by the original 30-function design
            timing = float(self.series[str(loopseen) + "_LoopTiming_Page Submit"])

            self.timing.append(timing)
            
            correct_postcon = RIGHT_POSTCONDITIONS[EVAL_ROWS.index(Function_Seen)]
            incorrect_postcon = WRONG_POSTCONDITIONS[EVAL_ROWS.index(Function_Seen)]
            postcondition_ratio = Levenshtein.ratio(correct_postcon, incorrect_postcon)  # similarity score

            if self.series["loop" + str(loopnum) + "num1"] == "3":
                Postcondition_Correct = 0
                postcondition_seen = WRONG_POSTCONDITIONS[EVAL_ROWS.index(Function_Seen)]
                metrics = classic_metrics(postcondition_seen)
                sm_metrics = WRONG_SM.iloc[EVAL_ROWS.index(Function_Seen)]
                assert not sm_metrics.isna().any(), f"no Shevrin & Maoz metrics for {Function_Seen}: {postcondition_seen}"
                type_check = WRONG_TYPE_CHECK[EVAL_ROWS.index(Function_Seen)]
                format_check = WRONG_FORMAT_CHECK[EVAL_ROWS.index(Function_Seen)]
                arithmetic_bounds = WRONG_ARITHMETIC_BOUNDS[EVAL_ROWS.index(Function_Seen)]
                arithmetic_equality = WRONG_ARITHMETIC_EQUALITY[EVAL_ROWS.index(Function_Seen)]
                container_property = WRONG_CONTAINER_PROPERTY[EVAL_ROWS.index(Function_Seen)]
                element_property = WRONG_ELEMENT_PROPERTY[EVAL_ROWS.index(Function_Seen)]
                forall_element_property = WRONG_FORALL_ELEMENT_PROPERTY[EVAL_ROWS.index(Function_Seen)]
                implication = WRONG_IMPLICATION[EVAL_ROWS.index(Function_Seen)]
                null_check = WRONG_NULL_CHECK[EVAL_ROWS.index(Function_Seen)]
                taxonomy_total = (type_check + format_check + arithmetic_bounds + arithmetic_equality + container_property + element_property + forall_element_property + implication + null_check)
                percentage_tests_failed = percentage_tests_failed_per_wrong_postcon[EVAL_ROWS.index(Function_Seen)]
            elif self.series["loop" + str(loopnum) + "num1"] == "8":
                Postcondition_Correct = 1
                postcondition_seen = RIGHT_POSTCONDITIONS[EVAL_ROWS.index(Function_Seen)]
                metrics = classic_metrics(postcondition_seen)
                sm_metrics = RIGHT_SM.iloc[EVAL_ROWS.index(Function_Seen)]
                assert not sm_metrics.isna().any(), f"no Shevrin & Maoz metrics for {Function_Seen}: {postcondition_seen}"
                type_check = RIGHT_TYPE_CHECK[EVAL_ROWS.index(Function_Seen)]
                format_check = RIGHT_FORMAT_CHECK[EVAL_ROWS.index(Function_Seen)]
                arithmetic_bounds = RIGHT_ARITHMETIC_BOUNDS[EVAL_ROWS.index(Function_Seen)]
                arithmetic_equality = RIGHT_ARITHMETIC_EQUALITY[EVAL_ROWS.index(Function_Seen)]
                container_property = RIGHT_CONTAINER_PROPERTY[EVAL_ROWS.index(Function_Seen)]
                element_property = RIGHT_ELEMENT_PROPERTY[EVAL_ROWS.index(Function_Seen)]
                forall_element_property = RIGHT_FORALL_ELEMENT_PROPERTY[EVAL_ROWS.index(Function_Seen)]
                implication = RIGHT_IMPLICATION[EVAL_ROWS.index(Function_Seen)]
                null_check = RIGHT_NULL_CHECK[EVAL_ROWS.index(Function_Seen)]
                taxonomy_total = (type_check + format_check + arithmetic_bounds + arithmetic_equality + container_property + element_property + forall_element_property + implication + null_check)
                percentage_tests_failed = percentage_tests_failed_per_right_postcon[EVAL_ROWS.index(Function_Seen)]
            else:
                print(self.series["loop" + str(loopnum) + "num1"])
                print("Wrong postcondition correctness", flush=True)
                exit(1)


            key = "loop" + str(loopnum) + "comm"

            if not key in self.series:
                Comment_Exists = 1
                if self.series["loop" + str(loopnum) + "num2"] == "1":
                    Comment_Type = "Incorrect"
                elif self.series["loop" + str(loopnum) + "num2"] == "2":
                    Comment_Type = "Overspecified"
                elif self.series["loop" + str(loopnum) + "num2"] == "3":
                    Comment_Type = "Underspecified"
                elif self.series["loop" + str(loopnum) + "num2"] == "4":
                    Comment_Type = "Exact"
                else:
                    print("Person " + str(self.row_template["Pid"]) + " on question " + "loop" + str(loopnum) + "num2 saw comment type " + self.series["loop" + str(loopnum) + "num2"], flush=True)
                    continue
            elif self.series["loop" + str(loopnum) + "comm"] == "0":
                Comment_Exists = 0
                Comment_Type = "None"
            elif self.series["loop" + str(loopnum) + "comm"] == "1":
                Comment_Exists = 1
                if (loopnum == 2) and self.series["loop" + str(loopnum) + "num2"] == "0":
                    continue
                elif self.series["loop" + str(loopnum) + "num2"] == "1":
                    Comment_Type = "Incorrect"
                elif self.series["loop" + str(loopnum) + "num2"] == "2":
                    Comment_Type = "Overspecified"
                elif self.series["loop" + str(loopnum) + "num2"] == "3":
                    Comment_Type = "Underspecified"
                elif self.series["loop" + str(loopnum) + "num2"] == "4":
                    Comment_Type = "Exact"
                else:
                    print("Person " + str(self.row_template["Pid"]) + " on question " + "loop" + str(loopnum) + "num2 saw comment type " + self.series["loop" + str(loopnum) + "num2"], flush=True)
                    continue
            else:
                print("Person " + str(self.row_template["Pid"]) + " on question " + "loop" + str(loopnum) + "num2 saw comment existence " + self.series["loop" + str(loopnum) + "comm"], flush=True)
                exit(1)

            if self.series[str(loopseen) + "_Pass"] == "yes, it is correct":
                chosen_passfail = 1
            elif self.series[str(loopseen) + "_Pass"] == "no, it is incorrect":
                chosen_passfail = 0
            else:
                print("Person " + str(self.row_template["Pid"]) + " on question " + str(loopseen) + "_Pass chose " + self.series[str(loopseen) + "_Pass"], flush=True)
                continue

            if chosen_passfail == Postcondition_Correct:
                Correct_Passfail = 1
            else:
                Correct_Passfail = 0

            Passfail_Confidence = self.series[str(loopseen) + "_Conf1_1"]
            if Passfail_Confidence == "":
                Passfail_Confidence = "0"
            if Passfail_Confidence == "attention check":
                print("Person " + str(self.row_template["Pid"]) + " on question " + str(loopseen) + "_Pass chose " + self.series[str(loopseen) + "_Conf1_1"], flush=True)
                continue
            if (self.series[str(loopseen) + "_Capture"] == "attention check"):
                print("Person " + str(self.row_template["Pid"]) + " on question " + str(loopseen) + "_Pass chose " + self.series[str(loopseen) + "_Capture"], flush=True)
                continue
            else:
                Capture = CAPTURE_MAP[self.series[str(loopseen) + "_Capture"]]
            Capture_Confidence = self.series[str(loopseen) + "_Conf2_1"]
            if Capture_Confidence == "":
                Capture_Confidence = "0"
            if Capture_Confidence == "attention check":
                print("Person " + str(self.row_template["Pid"]) + " on question " + str(loopseen) + "_Pass chose " + self.series[str(loopseen) + "_Conf2_1"], flush=True)
                continue
            new_row.update({
                "Function_Seen": Function_Seen,
                "Postcondition_Correct": Postcondition_Correct,
                "Comment_Exists": Comment_Exists,
                "Comment_Type": Comment_Type,
                "Participant_Correct": Correct_Passfail,
                "Response_Chosen": chosen_passfail,
                "Accuracy_Confidence": Passfail_Confidence,
                "Capture": Capture,
                "Actual Capture": actual_capture,
                "Capture_Confidence": Capture_Confidence,
                "Attention_Checks_Passed": attn_checks_passed,
                "Time_To_Complete": timing,
                "Postcondition_Seen": postcondition_seen,
                "Cognitive_Complexity_Postcondition": metrics['Cognitive'],
                "Cyclomatic_Complexity_Postcondition": metrics['Cyclomatic'],
                "Halstead_Difficulty_Postcondition": metrics['Halstead_Difficulty'],
                "SM_Formula": sm_metrics['SM_Formula'],
                **{name: sm_metrics[name] for name in PROPERTIES},   # the 11 Shevrin & Maoz properties and SM_Score
                "Cyclomatic_Complexity_Function": FUNCTION_METRICS[Function_Seen]['cyclomatic'],
                "Cognitive_Complexity_Function": FUNCTION_METRICS[Function_Seen]['cognitive'],
                "Halstead_Difficulty_Function": FUNCTION_METRICS[Function_Seen]['halstead_difficulty'],
                "SLOC_Function": FUNCTION_METRICS[Function_Seen]['sloc'],
                "Docstring_Words": FUNCTION_METRICS[Function_Seen]['docstring_words'],
                "Docstring_Examples": FUNCTION_METRICS[Function_Seen]['docstring_examples'],
                "Type_Check": type_check,
                "Format_Check": format_check,
                "Arithmetic_Bounds": arithmetic_bounds,
                "Arithmetic_Equality": arithmetic_equality,
                "Container_Property": container_property,
                "Element_Property": element_property,
                "Forall_Element_Property": forall_element_property,
                "Implication": implication,
                "Null_Check": null_check,
                "Postcondition_Ratio": postcondition_ratio,
                "Taxonomy_Total": taxonomy_total,
                "Percentage_Tests_Failed": percentage_tests_failed
            })
            yield new_row
        
        
class ResultsTable:

    def __init__(self, input_filename) -> None:
        data = pd.read_csv(input_filename, skipinitialspace=True)

        # First row of "data" is actually details about the questions.
        # self.question_series = data.iloc[0]
        # self.df = data.iloc[1:]
        self.df = data
        self.df = self.df.replace(np.nan, '', regex=True)

    def default_long_table_df(self):
        long_table_rows = []
        all_timing = []
        pid = 0
        for idx, row in self.df.iterrows():
            if idx == 0:
                continue
            if idx == 1:
                continue
            result = Result(row, pid)

            start = len(long_table_rows)
            for long_table_row in result.long_table_rows():
                long_table_rows.append(long_table_row)
            end = len(long_table_rows)
            
            if (end > start):
                pid += 1
                all_timing.extend(result.timing)

        average_threshold_1 = np.average(all_timing)
        stdev_threshold_1 = np.std(all_timing)

        min_threshold = 20  # average_threshold_1 - stdev_threshold_1
        count = 0
        for number in all_timing:
            if number < min_threshold:
                count += 1
        new_dataframe = pd.DataFrame.from_records(long_table_rows)
        # 1. Find all pids that have at least one too-fast row
        bad_pids = new_dataframe.loc[
            new_dataframe["Time_To_Complete"] < min_threshold, "Pid"
        ].unique()


        # Show all rows
        pd.set_option('display.max_rows', None)

        # Show full column width
        pd.set_option('display.max_colwidth', None)

        filtered_df = new_dataframe[~new_dataframe["Time_To_Complete"].lt(min_threshold)]

        filtered_df = new_dataframe[~new_dataframe["Time_To_Complete"].lt(min_threshold)]

        total_num = len(new_dataframe)
        num_dropped = total_num - len(filtered_df)

        return filtered_df

        return filtered_df
    
