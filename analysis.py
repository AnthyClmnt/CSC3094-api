import tokenize
from io import BytesIO
import math

python_keywords = [
    'if', 'elif', 'else',
    'while', 'for',
    'try', 'except', 'finally',
    'and', 'or', 'not',
    'def',
    'assert',
    'break', 'continue'
]

java_keywords = [
    'if', 'else if', 'else',
    'while', 'for',
    'switch', 'case', 'default',
    'try', 'catch', 'finally',
    'return', 'throw'
]

javascript_keywords = [
    'if', 'else if', 'else',
    'while', 'for',
    'switch', 'case', 'default',
    'try', 'catch', 'finally',
    'return', 'throw',
    '&&', '||', '!',
    'function',
    'pipe', 'subscribe'
]

html_keywords = [
    '<if>', '<else>',
    '<for>', '<while>',
    'onclick', 'onchange',
    'ngIf', 'ng',
    'created', 'mounted',
]


def calculate_cyclomatic_complexity(patch, filename):
    try:
        code = parse_github_patch(patch)
        file_extension = filename.split(".")[-1]
        keywords = []

        match file_extension:
            case "py":
                keywords += python_keywords
            case "java":
                keywords += java_keywords
            case "js":
                keywords += javascript_keywords
            case "ts":
                keywords += javascript_keywords
            case "html":
                keywords += html_keywords
            case _:
                return None

        complexity = 1

        tokens = tokenize.tokenize(BytesIO(code.encode('utf-8')).readline)
        for token in tokens:
            if token.type == tokenize.NAME and token.string in keywords:
                complexity += 1
        return complexity
    except:
        return None


def calculate_lines_to_comments_ratio(patch, filename):
    try:
        code = parse_github_patch(patch)
        file_extension = filename.split(".")[-1]
        comment_identifiers = []

        match file_extension:
            case "py":
                comment_identifiers += ["#", "'''", '"""']
            case "java":
                comment_identifiers += ["//", "/*"]
            case "js":
                comment_identifiers += ["//", "/*"]
            case "ts":
                comment_identifiers += ["//", "/*"]
            case "html":
                comment_identifiers += ["<!--"]
            case _:
                return None

        lines = code.split('\n')
        total_lines = len(lines)
        comment_lines = sum(
            1 for line in lines if any(line.strip().startswith(comment) for comment in comment_identifiers))

        if total_lines <= 2:
            return None
        else:
            return round(comment_lines / total_lines, 2)
    except Exception:
        return None


def calculate_halstead_volume(code, excluded_keywords):
    operators = set()
    operands = set()

    excluded_strings = {"(", ")", ":", ","}

    tokens = tokenize.tokenize(BytesIO(code.encode('utf-8')).readline)
    for token in tokens:
        if (token.type == tokenize.OP) and token.string not in excluded_strings:
            operators.add(token.string)
        elif (token.type == tokenize.NAME or token.type == tokenize.NUMBER) and token.string not in excluded_keywords:
            operands.add(token.string)

    n1 = len(operators)
    n2 = len(operands)

    volume = (n1 + n2) * math.log2(n1 + n2) if n1 + n2 > 0 else 0
    return round(volume, 1)


def calculate_maintainability_index(patch, filename, cc):
    try:
        code = parse_github_patch(patch)
        file_extension = filename.split(".")[-1]
        excluded_keywords = {}

        match file_extension:
            case "py":
                excluded_keywords = {'def', 'if', 'elif', 'else', 'while', 'for', 'return', 'in', 'range', 'pass',
                                     'break', 'continue', 'True', 'False', 'None', 'assert', 'async', 'await', 'with',
                                     'from', 'import', 'try', 'except', 'finally', 'raise', 'class', 'global',
                                     'nonlocal', 'lambda', 'yield', 'del', 'and', 'or', 'not', 'is', 'as', 'lambda'}
            case "java":
                excluded_keywords = {'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch', 'char',
                                     'class', 'const', 'continue', 'default', 'do', 'double', 'else', 'enum',
                                     'extends', 'final', 'finally', 'float', 'for', 'if', 'goto', 'implements',
                                     'import', 'instanceof', 'int', 'interface', 'long', 'native', 'new', 'package',
                                     'private', 'protected', 'public', 'return', 'short', 'static', 'strictfp',
                                     'super', 'switch', 'synchronized', 'this', 'throw', 'throws', 'transient', 'try',
                                     'void', 'volatile', 'while'}
            case "js":
                excluded_keywords = {'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger', 'default',
                                     'delete', 'do', 'else', 'export', 'extends', 'finally', 'for', 'function', 'if',
                                     'import', 'in', 'instanceof', 'new', 'return', 'super', 'switch', 'this', 'throw',
                                     'try', 'typeof', 'var', 'void', 'while', 'with', 'yield'}
            case "ts":
                excluded_keywords = {'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger', 'default',
                                     'delete', 'do', 'else', 'export', 'extends', 'finally', 'for', 'function', 'if',
                                     'import', 'in', 'instanceof', 'new', 'return', 'super', 'switch', 'this', 'throw',
                                     'try', 'typeof', 'var', 'void', 'while', 'with', 'yield'}

        if len(excluded_keywords) == 0:
            return None

        hv = calculate_halstead_volume(code, excluded_keywords)
        loc = len(code.splitlines())

        mi = 171 - 5.2 * math.log(hv) - 0.23 * cc - 16.2 * math.log(loc)
        return round(mi, 1)

    except Exception:
        return None


def parse_github_patch(patch_str):
    parsed_lines = []
    for line in patch_str.split('\n'):
        if line.startswith('+'):
            parsed_lines.append(line[1:])
    return '\n'.join(parsed_lines)
