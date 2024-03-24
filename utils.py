from cryptography.fernet import Fernet
import os
import datetime


def encryptToken(token: str):
    key = os.getenv('ENCRYPTION_KEY')
    f = Fernet(key)
    return f.encrypt(token.encode())


def decrypt_token(token: str):
    key = os.getenv('ENCRYPTION_KEY')
    f = Fernet(key)
    return f.decrypt(token).decode()


def unix_to_timeStamp(unix_time):
    unix_time_sec = unix_time / 1000
    converted_datetime = datetime.datetime.fromtimestamp(unix_time_sec)
    return converted_datetime


def grade_complexity(complexity):
    if complexity <= 10:
        gradeText = "low complexity"
        grade = "A"
        gradeClass = "low"
    elif 21 > complexity > 10:
        gradeText = "moderate complexity"
        grade = "B"
        gradeClass = "moderate"
    elif 41 > complexity > 20:
        gradeText = "high complexity"
        gradeClass = "high"
        grade = "C"
    else:
        gradeText = "very high complexity"
        gradeClass = "very-high"
        grade = "F"

    return gradeText, grade, gradeClass


def grade_maintainability(maintainability_index):
    if maintainability_index <= 50:
        grade = "A"
        grade_class = "low"
    elif 50 < maintainability_index <= 70:
        grade = "B"
        grade_class = "moderate"
    elif 70 < maintainability_index <= 85:
        grade = "C"
        grade_class = "high"
    else:
        grade = "F"
        grade_class = "very-high"

    return grade, grade_class


def grade_comment_ratio(ratio):
    if ratio <= 0.1:
        grade = "F"
        gradeClass = "very-high"
    elif 0.1 < ratio < 0.3:
        grade = "B"
        gradeClass = "moderate"
    else:
        grade = "A"
        gradeClass = "low"

    return grade, gradeClass
