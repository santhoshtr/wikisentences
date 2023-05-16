import re
import sys
from symbols import GLOBAL_SENTENCE_TERMINATORS
from typing import List

# the `(?<=...)` is a positive lookbehind assertion, which means that
# the regex engine will only match if the pattern is preceded by the given pattern.
# the `[%s]`` is a character class, which means that the regex engine
# will match any of the characters in the SENTENCE_TERMINATORS character group.
# the `\s+` is a quantifier, which means that the regex engine will
# match a whitespace character 1 or more times. Using the parenthesis we capture
# these whitespaces as a group

global_sent_split_pattern = re.compile(
    r"(?<=[%s])(\s+)" % "".join(GLOBAL_SENTENCE_TERMINATORS)
)


def findBoundary(text, match):
    tail = text[match.start()+1:]
    head = text[:match.start()]

    # Trailing non-final punctuation: not a sentence boundary
    if re.match(r'^[,;:]', tail):
        return None
    # Next word character is number or lower-case: not a sentence boundary
    if re.match(r'^\W*[0-9a-z]', tail):
        return None

    # Do not break in abbreviations. Example D. John, St. Peter
    lastWord = re.findall(r'\w*$', head)[-1]
    # Exclude at most 2 letter abbreviations. Examples: T. Dr. St. Jr. Sr. Ms. Mr.
    # But not all caps like "UK." as in  "UK. Not US",
    if len(lastWord)<=2 and re.match(r'^\W*[A-Z][a-z]?$', lastWord) and re.match(r'^\W*[A-Z]', tail):
        return None

    # Include any closing punctuation and trailing space
    return match.start() + 1 + len(re.match(r"^['”\"’]*\s*", tail).group(0))


def segment(text)->List[str]:
    boundaries = [0]
    matches = re.finditer(global_sent_split_pattern, text)
    for match in matches:
        boundary = findBoundary(text, match)
        if boundary is not None:
            boundaries.append(boundary)
    return [text[i:j] for i,j in zip(boundaries, boundaries[1:]+[None])]


if __name__ == "__main__":
    for line in sys.stdin:
        if len(line.strip()) > 1:
            sentences = segment(line)
            for sentence in sentences:
                if len(sentence.strip()) > 2: # Avoid very short sentences
                    print(sentence.strip())